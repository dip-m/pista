# similarity_engine.py
import json
from typing import List, Dict, Any, Optional, Set
import os

import numpy as np
import faiss
import psycopg2
from psycopg2.extensions import connection as psycopg2_connection

from backend.reasoning_utils import get_game_features, compute_meta_similarity, build_reason_summary
from backend.logger_config import logger
from .db import execute_query, get_connection, put_connection


class SimilarityEngine:
    def __init__(self, conn: psycopg2_connection, index, id_map: List[int]):
        self.conn = conn
        self.index = index
        self.id_map = id_map

        # precompute bgg_id -> index row
        self._id_to_index = {gid: i for i, gid in enumerate(id_map)}

    def _ensure_connection(self):
        """Ensure the database connection is alive, refresh if needed."""
        if self.conn is None:
            # No connection at all, get a new one
            logger.warning("No database connection, acquiring from pool")
            self.conn = get_connection()
            return

        try:
            # Test if connection is still alive
            cur = self.conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
        except (psycopg2.InterfaceError, psycopg2.OperationalError, AttributeError):
            # Connection is dead, get a new one
            logger.warning("Database connection closed, re-acquiring from pool")
            try:
                # Return old connection to pool if it exists (might fail, but that's ok)
                if self.conn is not None:
                    try:
                        if not self.conn.closed:
                            put_connection(self.conn)
                    except (AttributeError, Exception):
                        pass  # Ignore errors when returning dead connection
            except Exception:
                pass  # Ignore errors when returning dead connection
            # Get a new connection from the pool
            self.conn = get_connection()
            logger.info("Re-acquired database connection from pool")

    def _fetch_embedding(self, game_id: int) -> np.ndarray:
        """Fetch embedding for a game, with error handling and connection health check."""
        # Ensure connection is alive before using it
        self._ensure_connection()
        try:
            cur = execute_query(self.conn, "SELECT vector_json FROM game_embeddings WHERE game_id = %s", (game_id,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"No embedding found for game_id={game_id}")
                raise ValueError(f"No embedding found for game_id={game_id}")
            vec = np.array(json.loads(row[0]), dtype="float32")
            faiss.normalize_L2(vec.reshape(1, -1))
            return vec
        except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
            # Connection error - try once more with a fresh connection
            logger.warning(f"Connection error fetching embedding for game_id={game_id}, retrying: {e}")
            self._ensure_connection()
            try:
                cur = execute_query(self.conn, "SELECT vector_json FROM game_embeddings WHERE game_id = %s", (game_id,))
                row = cur.fetchone()
                if not row:
                    logger.warning(f"No embedding found for game_id={game_id}")
                    raise ValueError(f"No embedding found for game_id={game_id}")
                vec = np.array(json.loads(row[0]), dtype="float32")
                faiss.normalize_L2(vec.reshape(1, -1))
                return vec
            except Exception as retry_e:
                logger.error(f"Error fetching embedding for game_id={game_id} after retry: {retry_e}", exc_info=True)
                raise
        except (ValueError, json.JSONDecodeError, psycopg2.Error, Exception) as e:
            logger.error(f"Error fetching embedding for game_id={game_id}: {e}", exc_info=True)
            raise

    def _fetch_name(self, game_id: int) -> str:
        """Fetch game name, with connection health check."""
        self._ensure_connection()
        try:
            cur = execute_query(self.conn, "SELECT name FROM games WHERE id = %s", (game_id,))
            row = cur.fetchone()
            return row[0] if row else f"(id={game_id})"
        except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
            # Connection error - try once more with a fresh connection
            logger.warning(f"Connection error fetching name for game_id={game_id}, retrying: {e}")
            self._ensure_connection()
            try:
                cur = execute_query(self.conn, "SELECT name FROM games WHERE id = %s", (game_id,))
                row = cur.fetchone()
                return row[0] if row else f"(id={game_id})"
            except Exception as retry_e:
                logger.error(f"Error fetching name for game_id={game_id} after retry: {retry_e}")
                return f"(id={game_id})"

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
        use_rarity_weighting: bool = False,
        excluded_feature_values: Optional[Dict[str, Set[str]]] = None,
        required_feature_values: Optional[Dict[str, Set[str]]] = None,
        category_weight_only: bool = False,
        theme_only: bool = False,
        mechanics_only: bool = False,
        mechanics_weight: float = 0.5,
        categories_weight: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        constraints: generic constraint spec (see section 2).
        allowed_ids: if provided, restrict results to this set (e.g. user's collection).
        include_features: list of feature types to require (e.g., ['mechanics', 'categories'])
        exclude_features: list of feature types to exclude matches on
        """
        logger.debug(f"Searching similar to game_id={game_id}, top_k={top_k}, constraints={constraints}")

        # Ensure connection is healthy before starting search
        self._ensure_connection()

        # Initialize sims and idxs to avoid UnboundLocalError if exception occurs early
        sims = np.array([])
        idxs = []

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
                # Get embeddings for all games in collection - optimized batch fetch
                collection_ids = [gid for gid in allowed_ids if include_self or gid != game_id]

                if collection_ids:
                    # Batch fetch all embeddings in a single query
                    try:
                        placeholders = ",".join(["%s"] * len(collection_ids))
                        query = f"SELECT game_id, vector_json FROM game_embeddings WHERE game_id IN ({placeholders})"
                        cur = execute_query(self.conn, query, tuple(collection_ids))
                        rows = cur.fetchall()

                        collection_embeddings = []
                        valid_collection_ids = []
                        for row in rows:
                            gid, vec_json = row
                            try:
                                vec = np.array(json.loads(vec_json), dtype="float32")
                                collection_embeddings.append(vec)
                                valid_collection_ids.append(gid)
                            except (json.JSONDecodeError, ValueError) as e:
                                logger.warning(f"Error parsing embedding for game_id={gid}: {e}")
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
                    except Exception as e:
                        logger.error(f"Error batch fetching collection embeddings: {e}", exc_info=True)
                        # Fallback to empty results
                        sims = np.array([])
                        idxs = []
                else:
                    sims = np.array([])
                    idxs = []
            else:
                # search 2n matches to allow for reordering by weighted criteria
                # When searching in collection, search more candidates since filtering is strict
                # When excluding families, search even more to account for filtered results
                n_search = top_k * 2  # Default: Find 2n matches for reordering
                if allowed_ids is not None and len(allowed_ids) > 0:
                    # Search more candidates when filtering by collection to increase chance of finding matches
                    n_search = min(top_k * 10, len(self.id_map))  # Increased from 4x to 10x
                if excluded_feature_values and "families" in excluded_feature_values:
                    # When excluding families, search even more candidates to account for filtered results
                    n_search = max(n_search, top_k * 10)  # At least 10x top_k
                    n_search = min(n_search, len(self.id_map))  # But not more than available games
                sims, idxs = self.index.search(query_vec, n_search)
                sims = sims[0]
                idxs = idxs[0]
                # Convert index positions to game IDs
                idxs = [self.id_map[ix] if 0 <= ix < len(self.id_map) else -1 for ix in idxs]

            if explain:
                try:
                    # Ensure connection is healthy before getting features
                    self._ensure_connection()
                    # Validate game_id before calling get_game_features
                    if game_id is None:
                        raise ValueError("game_id cannot be None")
                    game_id = int(game_id)  # Ensure it's an integer
                    base_features = get_game_features(self.conn, game_id)
                except (ValueError, TypeError, psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                    # Connection error - try once more with a fresh connection
                    if isinstance(e, (psycopg2.InterfaceError, psycopg2.OperationalError)):
                        logger.warning(f"Connection error getting base features for game_id={game_id}, retrying: {e}")
                        self._ensure_connection()
                        try:
                            base_features = get_game_features(self.conn, game_id)
                        except Exception as retry_e:
                            logger.warning(f"Error getting base features for game_id={game_id} after retry: {retry_e}")
                            base_features = None
                            explain = False
                    else:
                        logger.warning(f"Error getting base features for game_id={game_id}: {e}")
                        base_features = None
                        explain = False  # Fall back to embedding-only search
                except psycopg2.Error as e:
                    logger.warning(f"Database error getting base features for game_id={game_id}: {e}")
                    base_features = None
                    explain = False  # Fall back to embedding-only search
        except Exception as e:
            logger.warning(f"Error getting details for game_id={game_id}: {e}")
            explain = False  # Fall back to embedding-only search

        results: List[Dict[str, Any]] = []
        total_candidates = 0
        filtered_out = {
            "invalid_index": 0,
            "self_excluded": 0,
            "not_in_allowed": 0,
            "failed_explain": 0,
            "required_features": 0,
            "excluded_features": 0,
        }

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

            # Validate gid before querying
            if gid is None:
                filtered_out["invalid_index"] += 1
                continue
            try:
                gid = int(gid)
            except (ValueError, TypeError):
                filtered_out["invalid_index"] += 1
                continue

            # Fetch additional game data including num_ratings, ranks_json, year_published, polls_json, min_players, max_players, description, designers for reordering
            try:
                # Ensure connection is healthy before querying
                self._ensure_connection()
                # Try to select avg_weight, but handle case where column might not exist
                try:
                    cur = execute_query(
                        self.conn,
                        "SELECT name, thumbnail, average_rating, num_ratings, ranks_json, year_published, polls_json, min_players, max_players, description, avg_weight FROM games WHERE id = %s",
                        (gid,),
                    )
                except psycopg2.Error as col_err:
                    # If avg_weight column doesn't exist, fall back to query without it
                    if "column" in str(col_err).lower() and "avg_weight" in str(col_err).lower():
                        logger.debug(f"avg_weight column not found, using query without it for game {gid}")
                        cur = execute_query(
                            self.conn,
                            "SELECT name, thumbnail, average_rating, num_ratings, ranks_json, year_published, polls_json, min_players, max_players, description FROM games WHERE id = %s",
                            (gid,),
                        )
                    else:
                        raise
            except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                # Connection error - try once more with a fresh connection
                logger.warning(f"Connection error fetching game {gid}, retrying: {e}")
                self._ensure_connection()
                try:
                    # Try to select avg_weight, but handle case where column might not exist
                    try:
                        cur = execute_query(
                            self.conn,
                            "SELECT name, thumbnail, average_rating, num_ratings, ranks_json, year_published, polls_json, min_players, max_players, description, avg_weight FROM games WHERE id = %s",
                            (gid,),
                        )
                    except psycopg2.Error as col_err:
                        # If avg_weight column doesn't exist, fall back to query without it
                        if "column" in str(col_err).lower() and "avg_weight" in str(col_err).lower():
                            logger.debug(f"avg_weight column not found in retry, using query without it for game {gid}")
                            cur = execute_query(
                                self.conn,
                                "SELECT name, thumbnail, average_rating, num_ratings, ranks_json, year_published, polls_json, min_players, max_players, description FROM games WHERE id = %s",
                                (gid,),
                            )
                        else:
                            raise
                except Exception as retry_e:
                    logger.warning(f"SQL error fetching game {gid} after retry: {retry_e}")
                    filtered_out["failed_explain"] += 1
                    continue
            except (psycopg2.Error, Exception) as e:
                logger.warning(f"SQL error fetching game {gid}: {e}")
                filtered_out["failed_explain"] += 1
                continue
            game_row = cur.fetchone()
            if not game_row:
                filtered_out["failed_explain"] += 1
                continue

            # Safely access columns with proper bounds checking
            # Expected columns: name(0), thumbnail(1), average_rating(2), num_ratings(3), ranks_json(4),
            # year_published(5), polls_json(6), min_players(7), max_players(8), description(9), avg_weight(10)
            row_len = len(game_row)
            if row_len < 10:
                logger.warning(f"Game {gid} row has only {row_len} columns, expected at least 10. Skipping.")
                filtered_out["failed_explain"] += 1
                continue

            try:
                game_name = game_row[0] if game_row[0] else self._fetch_name(gid)
                thumbnail = game_row[1] if row_len > 1 and game_row[1] else None
                average_rating = float(game_row[2]) if row_len > 2 and game_row[2] is not None else None
                num_ratings = int(game_row[3]) if row_len > 3 and game_row[3] is not None else 0
                ranks_json_str = game_row[4] if row_len > 4 and game_row[4] else None
                year_published = int(game_row[5]) if row_len > 5 and game_row[5] is not None else None
                polls_json_str = game_row[6] if row_len > 6 and game_row[6] else None
                min_players = int(game_row[7]) if row_len > 7 and game_row[7] is not None else None
                max_players = int(game_row[8]) if row_len > 8 and game_row[8] is not None else None
                description = game_row[9] if row_len > 9 and game_row[9] else None
                # avg_weight is optional (column 10), may not exist in all databases
                avg_weight = float(game_row[10]) if row_len > 10 and game_row[10] is not None else None
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing game row for game {gid}: {e}, row length: {row_len}")
                filtered_out["failed_explain"] += 1
                continue

            # Get designers for this game
            designers = []
            try:
                # Connection should still be healthy from previous query, but check anyway
                self._ensure_connection()
                cur_designers = execute_query(
                    self.conn,
                    """SELECT d.name FROM designers d
                       JOIN game_designers gd ON gd.designer_id = d.id
                       WHERE gd.game_id = %s ORDER BY d.name""",
                    (gid,),
                )
                designers = [row[0] for row in cur_designers.fetchall()]
            except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                # Connection error - try once more
                logger.debug(f"Connection error fetching designers for game {gid}, retrying: {e}")
                self._ensure_connection()
                try:
                    cur_designers = execute_query(
                        self.conn,
                        """SELECT d.name FROM designers d
                           JOIN game_designers gd ON gd.designer_id = d.id
                           WHERE gd.game_id = %s ORDER BY d.name""",
                        (gid,),
                    )
                    designers = [row[0] for row in cur_designers.fetchall()]
                except Exception:
                    pass  # Ignore errors on retry
            except (psycopg2.Error, Exception):
                pass

            # Early exclusion: Check max_players constraint before expensive explain mode
            player_constraints = constraints.get("players", {})
            if player_constraints:
                exact_players = player_constraints.get("exact")
                if exact_players is not None and max_players is not None:
                    # Exclude if game's max_players is less than required player count
                    if max_players < exact_players:
                        filtered_out["failed_explain"] += 1
                        continue

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

            # Parse polls_json to get language_dependence
            language_dependence = None
            if polls_json_str:
                try:
                    polls_data = json.loads(polls_json_str)
                    language_dep = polls_data.get("language_dependence", {})
                    if isinstance(language_dep, dict):
                        language_results = language_dep.get("results", [])  # Fixed: renamed to avoid shadowing outer 'results'
                        # Find the level with most votes
                        max_votes = 0
                        for result in language_results:
                            if isinstance(result, dict):
                                level = result.get("level")
                                numvotes = result.get("numvotes", 0)
                                if level and numvotes > max_votes:
                                    max_votes = numvotes
                                    try:
                                        level_num = int(level)
                                        value = result.get("value", "")
                                        language_dependence = {"level": level_num, "value": value, "numvotes": numvotes}
                                    except (ValueError, TypeError):
                                        pass
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"Error parsing polls_json for game {gid}: {e}")
                    pass

            # Ensure we have at least a name and game_id
            if not game_name:
                game_name = self._fetch_name(gid)

            record: Dict[str, Any] = {
                "game_id": gid,
                "name": game_name or f"Game {gid}",
                "thumbnail": thumbnail,
                "average_rating": average_rating,
                "num_ratings": num_ratings,
                "rank": rank,
                "year_published": year_published,
                "description": description,
                "designers": designers,
                "embedding_similarity": float(sim) if sim is not None else 0.0,
                "language_dependence": language_dependence,
                "avg_weight": avg_weight,
            }

            # Check required feature values EARLY (before computing similarity)
            if required_feature_values:
                try:
                    self._ensure_connection()
                    other_features_check = get_game_features(self.conn, gid)
                except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                    # Connection error - try once more
                    logger.warning(f"Connection error getting features for game_id={gid}, retrying: {e}")
                    self._ensure_connection()
                    try:
                        other_features_check = get_game_features(self.conn, gid)
                    except Exception as retry_e:
                        logger.warning(f"Error getting features for game_id={gid} after retry: {retry_e}")
                        continue
                except (ValueError, psycopg2.Error) as e:
                    logger.warning(f"Error getting features for game_id={gid} to check required features: {e}")
                    # If we can't get features, skip this game (it likely doesn't exist or has invalid data)
                    continue

                should_skip = False
                for feature_type, required_values in required_feature_values.items():
                    # Normalize feature type name (e.g., "mechanics" -> check "mechanics" key)
                    feature_key = feature_type
                    if feature_key in other_features_check:
                        feature_set = (
                            other_features_check[feature_key]
                            if isinstance(other_features_check[feature_key], set)
                            else set(other_features_check[feature_key])
                        )
                        # Normalize feature names for case-insensitive comparison
                        # Filter out None values before normalizing
                        feature_set_normalized = {f.lower().strip() for f in feature_set if f is not None}
                        required_values_normalized = {v.lower().strip() for v in required_values if v is not None}

                        # Check if ALL required values are present (case-insensitive)
                        missing_values = required_values_normalized - feature_set_normalized
                        if missing_values:
                            logger.info(
                                f"Game {gid} ({other_features_check.get('name', 'unknown')}) missing required {feature_type} values: {missing_values}. Required: {required_values}, Has: {feature_set}"
                            )
                            should_skip = True
                            break
                    else:
                        # Game doesn't have this feature type at all, so it's missing required values
                        logger.info(
                            f"Game {gid} ({other_features_check.get('name', 'unknown')}) missing required {feature_type} values {required_values} (no {feature_type} at all)"
                        )
                        should_skip = True
                        break
                if should_skip:
                    filtered_out["required_features"] = filtered_out.get("required_features", 0) + 1
                    continue

            # Check excluded feature values EARLY (before computing similarity)
            # If a game has any excluded families, skip it entirely
            if excluded_feature_values:
                # Reuse other_features_check if we already fetched it for required features
                if required_feature_values and other_features_check:
                    other_features_exclude_check = other_features_check
                else:
                    try:
                        self._ensure_connection()
                        other_features_exclude_check = get_game_features(self.conn, gid)
                    except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                        # Connection error - try once more
                        logger.warning(f"Connection error getting features for game_id={gid} (exclude check), retrying: {e}")
                        self._ensure_connection()
                        try:
                            other_features_exclude_check = get_game_features(self.conn, gid)
                        except Exception as retry_e:
                            logger.warning(f"Error getting features for game_id={gid} after retry (exclude check): {retry_e}")
                            continue
                    except (ValueError, psycopg2.Error) as e:
                        logger.warning(f"Error getting features for game_id={gid} to check excluded features: {e}")
                        continue

                should_exclude = False
                for feature_type, excluded_values in excluded_feature_values.items():
                    feature_key = feature_type
                    if feature_key in other_features_exclude_check:
                        feature_set = (
                            other_features_exclude_check[feature_key]
                            if isinstance(other_features_exclude_check[feature_key], set)
                            else set(other_features_exclude_check[feature_key])
                        )
                        # Normalize feature names for case-insensitive comparison
                        feature_set_normalized = {f.lower().strip() for f in feature_set if f is not None}
                        excluded_values_normalized = {v.lower().strip() for v in excluded_values if v is not None}

                        # Log first game for debugging
                        if filtered_out.get("excluded_features", 0) == 0 and filtered_out.get("total_checked", 0) == 0:
                            logger.info(
                                f"DEBUG: First game check - gid={gid}, name={other_features_exclude_check.get('name', 'unknown')}, feature_type={feature_type}, excluded_values={list(excluded_values_normalized)}, game_families={list(feature_set_normalized)[:5]}"
                            )
                            filtered_out["total_checked"] = filtered_out.get("total_checked", 0) + 1

                        # Check if game has ANY excluded values - if so, skip it
                        overlap = excluded_values_normalized & feature_set_normalized
                        if overlap:
                            logger.info(
                                f"EXCLUDING game {gid} ({other_features_exclude_check.get('name', 'unknown')}) - has excluded {feature_type} values: {list(overlap)[:3]}... (total excluded: {len(excluded_values_normalized)}, game has: {len(feature_set_normalized)})"
                            )
                            should_exclude = True
                            break
                        else:
                            # Log first few games that pass to understand what's happening
                            if filtered_out.get("excluded_features", 0) < 3:
                                logger.info(
                                    f"PASSING game {gid} ({other_features_exclude_check.get('name', 'unknown')}) - no overlap with excluded {feature_type}. Excluded: {list(excluded_values_normalized)}, Game has: {list(feature_set_normalized)[:5]}"
                                )

                if should_exclude:
                    filtered_out["excluded_features"] = filtered_out.get("excluded_features", 0) + 1
                    continue

            if explain and base_features:
                try:
                    self._ensure_connection()
                    other_features = get_game_features(self.conn, gid)

                    # Note: We don't remove excluded values from other_features anymore
                    # because we've already filtered out games with excluded families above

                    meta_score, overlaps, scores = compute_meta_similarity(
                        base_features,
                        other_features,
                        conn=self.conn,
                        use_rarity_weighting=use_rarity_weighting,
                        category_weight_only=category_weight_only,
                        theme_only=theme_only,
                        mechanics_only=mechanics_only,
                        mechanics_weight=mechanics_weight,
                        categories_weight=categories_weight,
                    )

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

                    # Check playtime constraints
                    if not self._satisfies_playtime_constraints(gid, constraints):
                        logger.debug(f"Game {gid} doesn't satisfy playtime constraints")
                        continue

                    # apply generic constraints
                    if not self._satisfies_constraints(scores, overlaps, constraints):
                        continue

                    final_score = 0.8 * record["embedding_similarity"] + 0.2 * meta_score
                    record["meta_similarity_score"] = meta_score
                    record["final_score"] = final_score
                    # Save game_id before update to prevent overwriting
                    saved_game_id = record.get("game_id")
                    record.update(overlaps)
                    # Restore game_id if it was overwritten
                    if "game_id" not in record or record.get("game_id") != saved_game_id:
                        record["game_id"] = saved_game_id

                    # Calculate missing and extra features (like "Do I need X" feature)
                    # Missing: features in base game but not in other game
                    missing_mechanics = sorted(base_features.get("mechanics", set()) - other_features.get("mechanics", set()))
                    missing_categories = sorted(
                        base_features.get("categories", set()) - other_features.get("categories", set())
                    )
                    missing_designers = sorted(base_features.get("designers", set()) - other_features.get("designers", set()))
                    missing_families = sorted(base_features.get("families", set()) - other_features.get("families", set()))

                    # Extra: features in other game but not in base game
                    extra_mechanics = sorted(other_features.get("mechanics", set()) - base_features.get("mechanics", set()))
                    extra_categories = sorted(other_features.get("categories", set()) - base_features.get("categories", set()))
                    extra_designers = sorted(other_features.get("designers", set()) - base_features.get("designers", set()))
                    extra_families = sorted(other_features.get("families", set()) - base_features.get("families", set()))

                    # Add missing and extra features to record
                    record["missing_mechanics"] = missing_mechanics
                    record["missing_categories"] = missing_categories
                    record["missing_designers"] = missing_designers
                    record["missing_families"] = missing_families
                    record["extra_mechanics"] = extra_mechanics
                    record["extra_categories"] = extra_categories
                    record["extra_designers"] = extra_designers
                    record["extra_families"] = extra_families

                    record["reason_summary"] = build_reason_summary(base_features, overlaps)
                except Exception as e:
                    logger.warning(f"Error processing game {gid} in explain mode: {e}", exc_info=True)
                    # Fall back to embedding-only for this game
                    record["final_score"] = record["embedding_similarity"]
                    record["reason_summary"] = "Similarity based on embeddings only"
            elif explain and not base_features:
                # explain=True but base_features unavailable - still try to get other_features for basic info
                try:
                    self._ensure_connection()
                    other_features = get_game_features(self.conn, gid)
                    # Can't compute meta_similarity without base_features, but we can still provide basic info
                    record["final_score"] = record["embedding_similarity"]
                    record["reason_summary"] = "Similarity based on embeddings only (base game features unavailable)"
                except Exception as e:
                    logger.debug(f"Could not get features for game {gid}: {e}")
                    record["final_score"] = record["embedding_similarity"]
                    record["reason_summary"] = "Similarity based on embeddings only"

            results.append(record)
            # Don't break early - collect all 2n matches for reordering

        # Reorder by weighted criteria: similarity score + num_ratings + rank + years since publish + complexity
        import time

        current_year = time.localtime().tm_year

        # Get base game complexity for comparison
        base_complexity = None
        if base_features:
            try:
                self._ensure_connection()
                cur = execute_query(
                    self.conn,
                    "SELECT avg_weight FROM games WHERE id = %s",
                    (game_id,),
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    base_complexity = float(row[0])
            except Exception:
                pass

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

            # complexity (avg_weight): prefer similar complexity, max weight 0.05
            complexity_weight = 0.0
            avg_weight = record.get("avg_weight")
            if avg_weight is not None and base_complexity is not None:
                complexity_diff = abs(avg_weight - base_complexity)
                # Normalize: difference of 0 = 1.0, difference of 5.0 = 0.0
                complexity_weight = 0.05 * max(0.0, 1.0 - (complexity_diff / 5.0))

            return base_score + ratings_weight + rank_weight + year_weight + complexity_weight

        # Sort by weighted score
        try:
            results.sort(key=calculate_weighted_score, reverse=True)
        except Exception as e:
            logger.error(f"Error sorting results: {e}", exc_info=True)
            # Fallback: sort by embedding similarity
            results.sort(key=lambda r: r.get("embedding_similarity", 0.0), reverse=True)

        # Return top_k after reordering
        # Log filtering summary
        if len(results) == 0 and total_candidates > 0:
            logger.warning(f"NO RESULTS after filtering! total_candidates: {total_candidates}, filtered_out: {filtered_out}")
            # Log more details about excluded features
            if excluded_feature_values:
                logger.warning(f"DEBUG: Excluded feature values: {excluded_feature_values}")
                if "families" in excluded_feature_values:
                    logger.warning(
                        f"DEBUG: Excluded families count: {len(excluded_feature_values['families'])}, families: {list(excluded_feature_values['families'])[:5]}"
                    )
        elif filtered_out.get("excluded_features", 0) > 0:
            logger.info(f"Filtering summary: {filtered_out}, total_candidates: {total_candidates}, results: {len(results)}")

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
        use_recommended = player_constraints.get("use_recommended", False)
        if exact_players is not None:
            # First check: max_players exclusion (already done early, but double-check here)
            if other_max is not None and other_max < exact_players:
                return False
            # Second check: min_players (game must support at least this many)
            if other_min is not None and other_min > exact_players:
                return False
            # Third check: If use_recommended is set, prefer recommended players from polls_json
            if use_recommended and other_recommended:
                if exact_players not in other_recommended:
                    # Not in recommended, but still check if it's in the supported range
                    if other_min is not None and other_max is not None:
                        if not (other_min <= exact_players <= other_max):
                            return False
                    else:
                        return False
            elif other_min is not None and other_max is not None:
                # Standard range check
                if not (other_min <= exact_players <= other_max):
                    return False
            elif not other_recommended:
                # No recommended players and no min/max, can't verify
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

    def _satisfies_playtime_constraints(
        self,
        game_id: int,
        constraints: Dict[str, Any],
    ) -> bool:
        """Check if playtime constraints are satisfied."""
        playtime_constraints = constraints.get("playtime", {})
        if not playtime_constraints:
            return True

        target_playtime = playtime_constraints.get("target")
        tolerance = playtime_constraints.get("tolerance", 0.3)

        if target_playtime is None:
            return True

        try:
            # Ensure connection is healthy before querying
            self._ensure_connection()
            # Fetch playing_time from database
            cur = execute_query(
                self.conn, "SELECT playing_time, min_playtime, max_playtime FROM games WHERE id = %s", (game_id,)
            )
            row = cur.fetchone()
            if not row:
                return True

            playing_time = int(row[0]) if row[0] is not None else None
            min_playing_time = int(row[1]) if row[1] is not None else None
            max_playing_time = int(row[2]) if row[2] is not None else None

            # Use playing_time if available, otherwise use min/max average
            if playing_time is not None:
                actual_time = playing_time
            elif min_playing_time is not None and max_playing_time is not None:
                actual_time = (min_playing_time + max_playing_time) / 2
            elif min_playing_time is not None:
                actual_time = min_playing_time
            elif max_playing_time is not None:
                actual_time = max_playing_time
            else:
                # No playtime data available, allow it
                return True

            # Check if actual_time is within tolerance of target
            tolerance_range = target_playtime * tolerance
            min_time = target_playtime - tolerance_range
            max_time = target_playtime + tolerance_range

            return min_time <= actual_time <= max_time
        except (psycopg2.Error, ValueError, TypeError) as e:
            logger.warning(f"Error checking playtime constraints for game {game_id}: {e}")
            # On error, allow the game through (don't filter it out)
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
            j_key = f"j_{facet}"  # e.g. 'j_mechanics'
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
