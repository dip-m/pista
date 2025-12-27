"""
Feature blacklist utilities for excluding features from similarity calculations.
"""
from typing import Set, Dict, List, Optional, Any
from backend.db import execute_query
from backend.logger_config import logger


def get_blacklisted_features(conn, feature_type: Optional[str] = None) -> Set[str]:
    """
    Get all blacklisted feature names for a given feature type.

    Args:
        conn: Database connection
        feature_type: Optional feature type filter ('mechanics', 'categories', etc.)
                      If None, returns blacklisted features for all types

    Returns:
        Set of blacklisted feature names
    """
    try:
        blacklisted = set()

        # Get all active blacklist rules
        query = """SELECT keyword_phrase, feature_type, match_type
                   FROM feature_blacklist
                   WHERE is_active = TRUE"""
        cur = execute_query(conn, query)
        rules = cur.fetchall()

        # For each rule, find matching features
        for keyword_phrase, fb_feature_type, match_type in rules:
            # Determine which feature types to check
            types_to_check = (
                [feature_type]
                if feature_type
                else ["mechanics", "categories", "families", "designers", "artists", "publishers"]
            )

            for ft in types_to_check:
                # Skip if rule is type-specific and doesn't match
                if fb_feature_type is not None and fb_feature_type != ft:
                    continue

                try:
                    if match_type == "exact":
                        query_match = f"SELECT name FROM {ft} WHERE LOWER(name) = LOWER(%s)"
                    else:
                        query_match = f"SELECT name FROM {ft} WHERE LOWER(name) LIKE LOWER(%s)"
                    pattern = keyword_phrase if match_type == "exact" else f"%{keyword_phrase}%"
                    cur_match = execute_query(conn, query_match, (pattern,))
                    for match_row in cur_match.fetchall():
                        blacklisted.add(match_row[0])
                except Exception as e:
                    logger.warning(f"Error matching features in {ft} for keyword '{keyword_phrase}': {e}")
                    continue

        return blacklisted
    except Exception as e:
        logger.error(f"Error getting blacklisted features: {e}", exc_info=True)
        return set()


def filter_blacklisted_features(conn, features: Set[str], feature_type: str) -> Set[str]:
    """
    Filter out blacklisted features from a feature set.

    Args:
        conn: Database connection
        features: Set of feature names to filter
        feature_type: Type of features ('mechanics', 'categories', etc.)

    Returns:
        Filtered set of features with blacklisted ones removed
    """
    blacklisted = get_blacklisted_features(conn, feature_type)
    return features - blacklisted


def find_matching_features(
    conn, keyword_phrase: str, feature_type: Optional[str] = None, match_type: str = "partial"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Find all features matching a keyword/phrase across feature types.

    Args:
        conn: Database connection
        keyword_phrase: Keyword or phrase to search for
        feature_type: Optional feature type filter
        match_type: 'partial' or 'exact'

    Returns:
        Dict mapping feature_type to list of matching features with id and name
    """
    results = {}
    feature_types = (
        [feature_type] if feature_type else ["mechanics", "categories", "families", "designers", "artists", "publishers"]
    )

    for ft in feature_types:
        try:
            if match_type == "exact":
                query = f"SELECT id, name FROM {ft} WHERE LOWER(name) = LOWER(%s) ORDER BY name"
            else:
                query = f"SELECT id, name FROM {ft} WHERE LOWER(name) LIKE LOWER(CONCAT('%%', %s, '%%')) ORDER BY name"
            cur = execute_query(conn, query, (keyword_phrase,))
            matches = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
            if matches:
                results[ft] = matches
        except Exception as e:
            logger.error(f"Error finding matching features in {ft}: {e}")
            continue

    return results
