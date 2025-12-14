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

            # search more than top_k to allow later filtering
            n_search = max(top_k + 20, top_k * 2)  # Search more to account for filtering
            sims, idxs = self.index.search(query_vec, n_search)
            sims = sims[0]
            idxs = idxs[0]

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

        for sim, ix in zip(sims, idxs):
            if ix < 0 or ix >= len(self.id_map):
                continue
            gid = self.id_map[ix]

            if not include_self and gid == game_id:
                continue

            if allowed_ids is not None and gid not in allowed_ids:
                # "Closest in my collection" = just pass allowed_ids=user_collection_ids
                continue

            # Fetch additional game data
            cur = self.conn.execute(
                "SELECT name, thumbnail, average_rating FROM games WHERE id = ?",
                (gid,)
            )
            game_row = cur.fetchone()
            game_name = game_row[0] if game_row else self._fetch_name(gid)
            thumbnail = game_row[1] if game_row and game_row[1] else None
            average_rating = float(game_row[2]) if game_row and game_row[2] is not None else None
            
            record: Dict[str, Any] = {
                "game_id": gid,
                "name": game_name,
                "thumbnail": thumbnail,
                "average_rating": average_rating,
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
            if len(results) >= top_k:
                break

        # final sorting
        if explain:
            results.sort(key=lambda r: r["final_score"], reverse=True)
        else:
            results.sort(key=lambda r: r["embedding_similarity"], reverse=True)

        return results

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

