# similarity_engine.py
import json
from typing import List, Dict, Any, Optional, Set

import numpy as np
import faiss
import sqlite3

from backend.reasoning_utils import get_game_features, compute_meta_similarity, build_reason_summary
from backend.logger_config import logger


class SimilarityEngine:
    def __init__(self, conn: sqlite3.Connection, index, id_map: List[int]):
        self.conn = conn
        self.index = index
        self.id_map = id_map

        # precompute bgg_id -> index row
        self._id_to_index = {gid: i for i, gid in enumerate(id_map)}

    def _fetch_embedding(self, game_id: int) -> np.ndarray:
        """Fetch embedding for a game, with error handling."""
        try:
            cur = self.conn.execute(
                "SELECT vector_json FROM game_embeddings WHERE game_id = ?",
                (game_id,)
            )
            row = cur.fetchone()
            if not row:
                logger.warning(f"No embedding found for game_id={game_id}")
                raise ValueError(f"No embedding found for game_id={game_id}")
            vec = np.array(json.loads(row[0]), dtype="float32")
            faiss.normalize_L2(vec.reshape(1, -1))
            return vec
        except (ValueError, json.JSONDecodeError, sqlite3.Error) as e:
            logger.error(f"Error fetching embedding for game_id={game_id}: {e}", exc_info=True)
            raise

    def _fetch_name(self, game_id: int) -> str:
        cur = self.conn.execute("SELECT name FROM games WHERE id = ?", (game_id,))
        row = cur.fetchone()
        return row[0] if row else f"(id={game_id})"

    def search_similar(
        self,
        game_id: int,
        top_k: int = 10,
        include_self: bool = False,
        constraints: Optional[Dict[str, Any]] = None,
        allowed_ids: Optional[Set[int]] = None,
        explain: bool = True,
        include_features: Optional[List[str]] = None,
        exclude_features: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        constraints: generic constraint spec (see section 2).
        allowed_ids: if provided, restrict results to this set (e.g. user's collection).
        include_features: list of feature types to require (e.g., ['mechanics', 'categories'])
        exclude_features: list of feature types to exclude matches on
        """
        logger.debug(f"Searching similar to game_id={game_id}, top_k={top_k}, constraints={constraints}")
        
        try:
            constraints = constraints or {}
            query_vec = self._fetch_embedding(game_id).reshape(1, -1)

            # When searching in a collection, try direct collection search first if collection is small enough
            # This ensures we find similar games even if they're not in top embedding candidates
            use_direct_collection_search = False
            if allowed_ids is not None and len(allowed_ids) > 0 and len(allowed_ids) <= 500:
                # For collections <= 500 games, compute similarity directly for all games in collection
                use_direct_collection_search = True
                logger.debug(f"Using direct collection search for {len(allowed_ids)} games")
            
            if use_direct_collection_search:
                # Get embeddings for all games in collection
                collection_ids = list(allowed_ids)
                collection_embeddings = []
                valid_collection_ids = []
                for gid in collection_ids:
                    if gid == game_id and not include_self:
                        continue
                    try:
                        vec = self._fetch_embedding(gid)
                        collection_embeddings.append(vec)
                        valid_collection_ids.append(gid)
                    except Exception:
                        continue
                
                if collection_embeddings:
                    # Compute cosine similarity for all games in collection
                    collection_matrix = np.vstack(collection_embeddings)
                    faiss.normalize_L2(collection_matrix)
                    similarities = np.dot(collection_matrix, query_vec.T).flatten()
                    
                    # Sort by similarity descending
                    sorted_indices = np.argsort(similarities)[::-1]
                    sims = similarities[sorted_indices]
                    idxs = [valid_collection_ids[i] for i in sorted_indices]
                else:
                    sims = np.array([])
                    idxs = []
            else:
                # search 2n matches to allow for reordering by weighted criteria
                # When searching in collection, search more candidates since filtering is strict
                n_search = top_k * 2  # Default: Find 2n matches for reordering
                if allowed_ids is not None and len(allowed_ids) > 0:
                    # Search more candidates when filtering by collection to increase chance of finding matches
                    n_search = min(top_k * 10, len(self.id_map))  # Increased from 4x to 10x
                sims, idxs = self.index.search(query_vec, n_search)
                sims = sims[0]
                idxs = idxs[0]
                # Convert index positions to game IDs
                idxs = [self.id_map[ix] if 0 <= ix < len(self.id_map) else -1 for ix in idxs]

            if explain:
                try:
                    base_features = get_game_features(self.conn, game_id)
                except Exception as e:
                    logger.warning(f"Error getting base features for game_id={game_id}: {e}")
                    explain = False  # Fall back to embedding-only search
        except Exception as e:
            logger.warning(f"Error getting details for game_id={game_id}: {e}")
            explain = False  # Fall back to embedding-only search
        
        results: List[Dict[str, Any]] = []
        total_candidates = 0
        filtered_out = {"invalid_index": 0, "self_excluded": 0, "not_in_allowed": 0, "failed_explain": 0}
        
        for sim, gid_or_ix in zip(sims, idxs):
            total_candidates += 1
            # In direct collection search, gid_or_ix is already the game ID
            # In regular search, gid_or_ix is already converted from index to game ID
            if gid_or_ix < 0:
                filtered_out["invalid_index"] += 1
                continue
            gid = gid_or_ix

            if not include_self and gid == game_id:
                filtered_out["self_excluded"] += 1
                continue

            if allowed_ids is not None and gid not in allowed_ids:
                filtered_out["not_in_allowed"] += 1
                # "Closest in my collection" = just pass allowed_ids=user_collection_ids
                continue

            # Fetch additional game data including num_ratings, ranks_json, year_published for reordering
            cur = self.conn.execute(
                "SELECT name, thumbnail, average_rating, num_ratings, ranks_json, year_published FROM games WHERE id = ?",
                (gid,)
            )
            game_row = cur.fetchone()
            game_name = game_row[0] if game_row else self._fetch_name(gid)
            thumbnail = game_row[1] if game_row and game_row[1] else None
            average_rating = float(game_row[2]) if game_row and game_row[2] is not None else None
            num_ratings = int(game_row[3]) if game_row and game_row[3] is not None else 0
            ranks_json_str = game_row[4] if game_row and game_row[4] else None
            year_published = int(game_row[5]) if game_row and game_row[5] is not None else None
            
            # Parse ranks_json to get best rank (overall, or category-specific)
            rank = None
            if ranks_json_str:
                try:
                    ranks_data = json.loads(ranks_json_str)
                    # ranks_json structure from parser: {"ranks": [{"value": "123", "friendlyname": "boardgame", ...}, ...]}
                    # But it might also be stored as a list directly in some cases
                    rank_list = []
                    if isinstance(ranks_data, dict):
                        rank_list = ranks_data.get("ranks", [])
                    elif isinstance(ranks_data, list):
                        rank_list = ranks_data
                    
                    if isinstance(rank_list, list) and len(rank_list) > 0:
                        # Look for overall rank (friendlyname contains "boardgame" or name="boardgame")
                        for rank_entry in rank_list:
                            if isinstance(rank_entry, dict):
                                friendlyname = rank_entry.get("friendlyname", "").lower()
                                name = rank_entry.get("name", "").lower()
                                # Match "boardgame" or "Board Game Rank" etc.
                                if "boardgame" in friendlyname or name == "boardgame":
                                    rank_value = rank_entry.get("value")
                                    if rank_value and rank_value != "Not Ranked":
                                        try:
                                            rank = int(rank_value)
                                            break
                                        except (ValueError, TypeError):
                                            pass
                        # If no overall rank, try first available rank
                        if rank is None:
                            for rank_entry in rank_list:
                                if isinstance(rank_entry, dict):
                                    rank_value = rank_entry.get("value")
                                    if rank_value and rank_value != "Not Ranked":
                                        try:
                                            rank = int(rank_value)
                                            break
                                        except (ValueError, TypeError):
                                            pass
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"Error parsing ranks_json for game {gid}: {e}")
                    pass
            
            record: Dict[str, Any] = {
                "game_id": gid,
                "name": game_name,
                "thumbnail": thumbnail,
                "average_rating": average_rating,
                "num_ratings": num_ratings,
                "rank": rank,
                "year_published": year_published,
                "embedding_similarity": float(sim),
            }

            if explain:
                try:
                    other_features = get_game_features(self.conn, gid)
                    meta_score, overlaps, scores = compute_meta_similarity(base_features, other_features)

                    # Check include/exclude features
                    if include_features:
                        if not self._has_required_features(overlaps, include_features):
                            logger.debug(f"Game {gid} missing required features {include_features}")
                            continue
                    
                    if exclude_features:
                        if self._has_excluded_features(overlaps, exclude_features):
                            logger.debug(f"Game {gid} has excluded features {exclude_features}")
                            continue
                    
                    # Check player count constraints (before generic constraints)
                    if not self._satisfies_player_constraints(base_features, other_features, constraints):
                        logger.debug(f"Game {gid} doesn't satisfy player constraints")
                        continue
                    
                    # apply generic constraints
                    if not self._satisfies_constraints(scores, overlaps, constraints):
                        continue

                    final_score = 0.8 * record["embedding_similarity"] + 0.2 * meta_score
                    record["meta_similarity_score"] = meta_score
                    record["final_score"] = final_score
                    record.update(overlaps)
                    record["reason_summary"] = build_reason_summary(base_features, overlaps)
                except Exception as e:
                    logger.warning(f"Error processing game {gid} in explain mode: {e}")
                    # Fall back to embedding-only for this game
                    record["final_score"] = record["embedding_similarity"]
                    record["reason_summary"] = "Similarity based on embeddings only"

            results.append(record)
            # Don't break early - collect all 2n matches for reordering

        # Reorder by weighted criteria: similarity score + num_ratings + rank + years since publish
        import time
        current_year = time.localtime().tm_year
        
        def calculate_weighted_score(record):
            base_score = record.get("final_score", record.get("embedding_similarity", 0.0))
            
            # Normalize and weight factors
            # num_ratings: log scale, max weight 0.1
            num_ratings = record.get("num_ratings", 0)
            ratings_weight = 0.1 * min(1.0, (num_ratings / 10000.0) if num_ratings > 0 else 0)
            
            # rank: better rank (lower number) = higher score, max weight 0.1
            rank = record.get("rank")
            rank_weight = 0.0
            if rank is not None and rank > 0:
                # Normalize: rank 1 = 1.0, rank 10000 = 0.0
                rank_weight = 0.1 * max(0.0, 1.0 - (rank / 10000.0))
            
            # years since publish: newer games get slight boost, max weight 0.05
            year = record.get("year_published")
            year_weight = 0.0
            if year is not None:
                years_ago = current_year - year
                # Games from last 5 years get full boost, older games get less
                year_weight = 0.05 * max(0.0, 1.0 - (years_ago / 20.0))
            
            return base_score + ratings_weight + rank_weight + year_weight
        
        # Sort by weighted score
        results.sort(key=calculate_weighted_score, reverse=True)
        
        # Return top_k after reordering
        return results[:top_k]

    def _satisfies_player_constraints(
        self,
        base_features: Dict[str, Any],
        other_features: Dict[str, Any],
        constraints: Dict[str, Any],
    ) -> bool:
        """Check if player count constraints are satisfied."""
        player_constraints = constraints.get("players", {})
        if not player_constraints:
            return True
        
        base_min = base_features.get("min_players")
        base_max = base_features.get("max_players")
        base_recommended = base_features.get("recommended_players", set())
        base_best = base_features.get("best_player_count")
        
        other_min = other_features.get("min_players")
        other_max = other_features.get("max_players")
        other_recommended = other_features.get("recommended_players", set())
        other_best = other_features.get("best_player_count")
        
        # Check exact player count
        exact_players = player_constraints.get("exact")
        if exact_players is not None:
            if other_min is not None and other_max is not None:
                if not (other_min <= exact_players <= other_max):
                    return False
            elif exact_players not in other_recommended:
                return False
        
        # Check player count range overlap
        min_overlap = player_constraints.get("min_overlap")
        if min_overlap is not None:
            if base_min is not None and base_max is not None and other_min is not None and other_max is not None:
                # Check if ranges overlap
                range_overlap = max(0, min(base_max, other_max) - max(base_min, other_min) + 1)
                if range_overlap < min_overlap:
                    return False
            elif base_recommended and other_recommended:
                # Check recommended players overlap
                overlap = len(base_recommended & other_recommended)
                if overlap < min_overlap:
                    return False
        
        # Check similar best player count
        similar_best = player_constraints.get("similar_best")
        if similar_best and base_best is not None and other_best is not None:
            if abs(base_best - other_best) > 1:  # Allow 1 player difference
                return False
        
        return True

    def _satisfies_constraints(
        self,
        scores: Dict[str, float],
        overlaps: Dict[str, Any],
        constraints: Dict[str, Any],
    ) -> bool:
        """
        Generic constraint checker for things like:
        - "mechanics.jaccard >= 0.6"
        - "categories.jaccard <= 0.2"
        - "designers.overlap >= 1"
        All encoded in a config dict (see next section).
        """
        # Example expected shape:
        # {
        #   "mechanics": {"jaccard_min": 0.6},
        #   "categories": {"jaccard_max": 0.2},
        #   "designers": {"min_overlap": 1},
        # }

        for facet, cfg in constraints.items():
            j_key = f"j_{facet}"          # e.g. 'j_mechanics'
            shared_key = f"shared_{facet}"  # e.g. 'shared_mechanics'

            j_val = scores.get(j_key)
            shared_list = overlaps.get(shared_key, [])

            j_min = cfg.get("jaccard_min")
            j_max = cfg.get("jaccard_max")
            min_overlap = cfg.get("min_overlap")
            max_overlap = cfg.get("max_overlap")

            if j_min is not None and (j_val is None or j_val < j_min):
                return False
            if j_max is not None and (j_val is None or j_val > j_max):
                return False
            if min_overlap is not None and len(shared_list) < min_overlap:
                return False
            if max_overlap is not None and len(shared_list) > max_overlap:
                return False

        return True
    
    def _has_required_features(self, overlaps: Dict[str, Any], include_features: List[str]) -> bool:
        """Check if game has at least one feature from each required type."""
        for feature_type in include_features:
            shared_key = f"shared_{feature_type}"
            if shared_key not in overlaps or len(overlaps[shared_key]) == 0:
                return False
        return True
    
    def _has_excluded_features(self, overlaps: Dict[str, Any], exclude_features: List[str]) -> bool:
        """Check if game has any features from excluded types (strict exclusion)."""
        for feature_type in exclude_features:
            shared_key = f"shared_{feature_type}"
            if shared_key in overlaps and len(overlaps[shared_key]) > 0:
                logger.debug(f"Game excluded due to {feature_type} overlap: {overlaps[shared_key]}")
                return True
        return False

