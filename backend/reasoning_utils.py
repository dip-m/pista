import math
import logging
from typing import Dict, Set, List, Tuple, Optional, Any

from .db import execute_query
from .feature_blacklist import filter_blacklisted_features

logger = logging.getLogger(__name__)


def _fetch_name(conn, game_id: int) -> str:
    if game_id is None:
        raise ValueError("game_id cannot be None")
    try:
        game_id = int(game_id)
    except (ValueError, TypeError):
        raise ValueError(f"game_id must be an integer, got {type(game_id)}: {game_id}")

    try:
        cur = execute_query(conn, "SELECT name FROM games WHERE id = %s", (game_id,))
        row = cur.fetchone()
        return row[0] if row else f"(id={game_id})"
    except Exception as e:
        logger.error(f"SQL error fetching name for game_id={game_id}: {e}")
        return f"(id={game_id})"


def _fetch_feature_names(
    conn,
    game_id: int,
    join_table: str,
    vocab_table: str,
    join_col_game: str,
    join_col_vocab: str,
) -> Set[str]:
    if game_id is None:
        raise ValueError("game_id cannot be None")
    try:
        game_id = int(game_id)
    except (ValueError, TypeError):
        raise ValueError(f"game_id must be an integer, got {type(game_id)}: {game_id}")

    try:
        sql = f"""SELECT v.name
                   FROM {vocab_table} v
                   JOIN {join_table} j ON j.{join_col_vocab} = v.id
                   WHERE j.{join_col_game} = %s
                   ORDER BY v.name"""
        cur = execute_query(conn, sql, (game_id,))
        return {row[0] for row in cur.fetchall()}
    except Exception as e:
        logger.error(f"SQL error in _fetch_feature_names for game_id={game_id}, table={vocab_table}: {e}")
        return set()


def get_game_features(conn, game_id: int) -> Dict[str, object]:
    # Validate game_id
    if game_id is None:
        raise ValueError("game_id cannot be None")
    try:
        game_id = int(game_id)
    except (ValueError, TypeError):
        raise ValueError(f"game_id must be an integer, got {type(game_id)}: {game_id}")

    name = _fetch_name(conn, game_id)

    def fetch(join_table, vocab_table, join_vocab_col):
        try:
            sql = f"""SELECT v.name
                       FROM {vocab_table} v
                       JOIN {join_table} j ON j.{join_vocab_col} = v.id
                       WHERE j.game_id = %s
                       ORDER BY v.name"""
            cur = execute_query(conn, sql, (game_id,))
            # Filter out None values and empty strings
            return {row[0] for row in cur.fetchall() if row[0] is not None and row[0].strip()}
        except Exception as e:
            logger.error(f"SQL error fetching {vocab_table} for game_id={game_id}: {e}")
            return set()  # Return empty set on error

    mechanics = fetch("game_mechanics", "mechanics", "mechanic_id")
    categories = fetch("game_categories", "categories", "category_id")
    families = fetch("game_families", "families", "family_id")
    designers = fetch("game_designers", "designers", "designer_id")
    artists = fetch("game_artists", "artists", "artist_id")
    publishers = fetch("game_publishers", "publishers", "publisher_id")

    # Filter out blacklisted features
    mechanics = filter_blacklisted_features(conn, mechanics, "mechanics")
    categories = filter_blacklisted_features(conn, categories, "categories")
    families = filter_blacklisted_features(conn, families, "families")
    designers = filter_blacklisted_features(conn, designers, "designers")
    artists = filter_blacklisted_features(conn, artists, "artists")
    publishers = filter_blacklisted_features(conn, publishers, "publishers")

    # Apply feature modifications from FeatureMod table
    cur = execute_query(
        conn,
        """SELECT feature_type, feature_id, action
           FROM feature_mods
           WHERE game_id = %s
           ORDER BY created_at DESC""",
        (game_id,),
    )
    mods = cur.fetchall()

    # Create feature type to table mapping
    feature_tables = {
        "mechanics": ("mechanics", mechanics),
        "categories": ("categories", categories),
        "families": ("families", families),
        "designers": ("designers", designers),
        "artists": ("artists", artists),
        "publishers": ("publishers", publishers),
    }

    # Apply modifications
    for mod in mods:
        feature_type = mod[0]
        feature_id = mod[1]
        action = mod[2]

        if feature_type not in feature_tables:
            continue

        table_name, feature_set = feature_tables[feature_type]

        # Get feature name
        cur = execute_query(conn, f"SELECT name FROM {table_name} WHERE id = %s", (feature_id,))
        row = cur.fetchone()
        if row:
            feature_name = row[0]
            if action == "add":
                feature_set.add(feature_name)
            elif action == "remove":
                feature_set.discard(feature_name)

    # Get player count info from games table and polls_json
    cur = execute_query(conn, "SELECT min_players, max_players, polls_json FROM games WHERE id = %s", (game_id,))
    player_row = cur.fetchone()
    min_players = player_row[0] if player_row and player_row[0] else None
    max_players = player_row[1] if player_row and player_row[1] else None
    polls_json_str = player_row[2] if player_row and player_row[2] else None

    # Parse polls_json to get recommended player counts
    recommended_players = set()
    best_player_count = None
    if polls_json_str:
        try:
            import json

            polls_data = json.loads(polls_json_str)
            suggested_players = polls_data.get("suggested_numplayers", {})
            if isinstance(suggested_players, dict):
                results = suggested_players.get("results", [])
                max_best_votes = 0
                for result in results:
                    if isinstance(result, dict):
                        numplayers = result.get("numplayers")
                        votes = result.get("votes", {})
                        # Count "Best" votes
                        best_votes = votes.get("Best", 0)
                        recommended_votes = votes.get("Recommended", 0)
                        if best_votes > 0 or recommended_votes > 0:
                            try:
                                player_num = int(numplayers.replace("+", "").split()[0])
                                recommended_players.add(player_num)
                                if best_votes > max_best_votes:
                                    max_best_votes = best_votes
                                    best_player_count = player_num
                            except (ValueError, AttributeError):
                                pass
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    return {
        "id": game_id,
        "name": name,
        "mechanics": mechanics,
        "categories": categories,
        "families": families,
        "designers": designers,
        "artists": artists,
        "publishers": publishers,
        "min_players": min_players,
        "max_players": max_players,
        "recommended_players": recommended_players,
        "best_player_count": best_player_count,
    }


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union) if union else 0.0


def get_feature_rarity_weights(conn, feature_type: str) -> Dict[str, float]:
    """Calculate rarity weights for features. Rarer features get higher weights."""
    # Map feature types to their tables
    table_map = {
        "mechanics": ("game_mechanics", "mechanic_id", "mechanics"),
        "categories": ("game_categories", "category_id", "categories"),
        "families": ("game_families", "family_id", "families"),
        "designers": ("game_designers", "designer_id", "designers"),
        "artists": ("game_artists", "artist_id", "artists"),
        "publishers": ("game_publishers", "publisher_id", "publishers"),
    }

    if feature_type not in table_map:
        return {}

    join_table, join_col, vocab_table = table_map[feature_type]

    # Get total number of games
    cur = execute_query(conn, "SELECT COUNT(DISTINCT id) FROM games")
    total_games = cur.fetchone()[0] or 1

    # Get frequency of each feature
    cur = execute_query(
        conn,
        f"""SELECT v.name, COUNT(DISTINCT j.game_id) as count
           FROM {vocab_table} v
           JOIN {join_table} j ON j.{join_col} = v.id
           GROUP BY v.id, v.name""",
    )

    weights = {}
    for row in cur.fetchall():
        feature_name = row[0]
        count = row[1]
        # Rarity = inverse frequency (less common = higher weight)
        # Normalize: weight = 1 / (frequency / total_games)
        # Add smoothing to avoid division by zero
        frequency = count / total_games
        weight = 1.0 / (frequency + 0.001)  # Add small smoothing factor
        # Normalize weights to reasonable range (0.5 to 3.0) - wider range for more impact
        # Use log scale to make differences more pronounced
        normalized_weight = math.log(weight + 1) / math.log(1000)  # Normalize to 0-1 range
        weights[feature_name] = 0.5 + normalized_weight * 2.5  # Scale to 0.5-3.0 range

    return weights


def compute_meta_similarity(
    f1: Dict[str, object], f2: Dict[str, object], conn: Optional[Any] = None, use_rarity_weighting: bool = False
) -> Tuple[float, Dict[str, List[str]], Dict[str, float]]:
    mech1, mech2 = f1["mechanics"], f2["mechanics"]
    cat1, cat2 = f1["categories"], f2["categories"]
    fam1, fam2 = f1["families"], f2["families"]
    des1, des2 = f1["designers"], f2["designers"]
    art1, art2 = f1["artists"], f2["artists"]
    pub1, pub2 = f1["publishers"], f2["publishers"]

    # Filter out non-gameplay categories that shouldn't affect similarity
    # These are implementation/publishing categories, not gameplay features
    excluded_categories = {
        "Digital Implementation",
        "Crowdfunding",
        "Digital Game",
        "App Implementation",
        "Video Game Theme",
        "Software",
    }
    cat1 = cat1 - excluded_categories
    cat2 = cat2 - excluded_categories

    overlaps = {
        "shared_mechanics": sorted(mech1 & mech2),
        "shared_categories": sorted(cat1 & cat2),
        "shared_families": sorted(fam1 & fam2),
        "shared_designers": sorted(des1 & des2),
        "shared_artists": sorted(art1 & art2),
        "shared_publishers": sorted(pub1 & pub2),
    }

    scores = {
        "j_mechanics": jaccard(mech1, mech2),
        "j_categories": jaccard(cat1, cat2),
        "j_families": jaccard(fam1, fam2),
        "j_designers": jaccard(des1, des2),
        "j_artists": jaccard(art1, art2),
        "j_publishers": jaccard(pub1, pub2),
    }

    # Base weights - mechanics and categories are separate equal-weighted buckets
    # Mechanics bucket: 50% weight
    # Categories bucket: 50% weight (categories + families + themes)
    # Other features: minimal weight
    mechanics_weight = 0.50
    categories_weight = 0.50  # Categories, families, and theme-related features

    # Distribute categories_weight across categories and families (themes)
    categories_base_weight = 0.30  # Categories
    families_weight = 0.15  # Families (themes)
    # Remaining weight for other features
    other_weight = 0.05

    weights = {
        "mechanics": mechanics_weight,
        "categories": categories_base_weight,
        "families": families_weight,
        "designers": other_weight * 0.4,  # 0.02
        "artists": other_weight * 0.2,  # 0.01
        "publishers": other_weight * 0.4,  # 0.02
    }

    # Apply rarity weighting if enabled (applies to mechanics and categories buckets separately)
    mechanics_bucket_multiplier = 1.0
    categories_bucket_multiplier = 1.0

    if use_rarity_weighting and conn:
        # Get rarity weights for shared features
        rarity_weights = {}
        for feature_type in ["mechanics", "categories", "families"]:
            feature_rarity = get_feature_rarity_weights(conn, feature_type)
            rarity_weights[feature_type] = feature_rarity

        # Calculate rarity multipliers for mechanics bucket
        shared_mechanics = overlaps.get("shared_mechanics", [])
        if shared_mechanics and "mechanics" in rarity_weights:
            rarities = [rarity_weights["mechanics"].get(f, 1.0) for f in shared_mechanics]
            avg_rarity = sum(rarities) / len(rarities) if rarities else 1.0
            mechanics_bucket_multiplier = 1.0 + (avg_rarity - 1.0) * 3.0
            logger.info(
                f"Rarity weighting for mechanics bucket: avg_rarity={avg_rarity:.3f}, multiplier={mechanics_bucket_multiplier:.3f}"
            )

        # Calculate rarity multipliers for categories bucket (categories + families)
        shared_categories = overlaps.get("shared_categories", [])
        shared_families = overlaps.get("shared_families", [])
        all_theme_features = shared_categories + shared_families
        if all_theme_features:
            rarities = []
            if shared_categories and "categories" in rarity_weights:
                rarities.extend([rarity_weights["categories"].get(f, 1.0) for f in shared_categories])
            if shared_families and "families" in rarity_weights:
                rarities.extend([rarity_weights["families"].get(f, 1.0) for f in shared_families])
            if rarities:
                avg_rarity = sum(rarities) / len(rarities)
                categories_bucket_multiplier = 1.0 + (avg_rarity - 1.0) * 3.0
                logger.info(
                    f"Rarity weighting for categories bucket: avg_rarity={avg_rarity:.3f}, multiplier={categories_bucket_multiplier:.3f}"
                )

    # Calculate mechanics bucket score (50% weight) - apply rarity multiplier if enabled
    mechanics_bucket_score = scores["j_mechanics"] * mechanics_bucket_multiplier

    # Calculate categories bucket score (50% weight) - average of categories and families, apply rarity multiplier
    categories_bucket_score = ((scores["j_categories"] + scores["j_families"]) / 2.0) * categories_bucket_multiplier

    # Normalize multipliers to keep scores in [0, 1] range
    # We'll apply normalization after combining buckets
    max_multiplier = max(mechanics_bucket_multiplier, categories_bucket_multiplier, 1.0)
    if max_multiplier > 1.0:
        mechanics_bucket_score = mechanics_bucket_score / max_multiplier
        categories_bucket_score = categories_bucket_score / max_multiplier

    # Final score: 50% mechanics + 50% categories bucket
    meta_score = 0.50 * mechanics_bucket_score + 0.50 * categories_bucket_score

    return meta_score, overlaps, scores


def build_reason_summary(query_features: Dict[str, object], overlaps: Dict[str, List[str]]) -> str:
    bits: List[str] = []

    if overlaps["shared_designers"]:
        bits.append(f"shares designer(s) {', '.join(overlaps['shared_designers'])}")
    if overlaps["shared_mechanics"]:
        bits.append("shares mechanics like " + ", ".join(overlaps["shared_mechanics"][:3]))
    if overlaps["shared_categories"]:
        bits.append("similar themes/categories: " + ", ".join(overlaps["shared_categories"][:3]))
    if overlaps["shared_families"]:
        bits.append("is in related family lines: " + ", ".join(overlaps["shared_families"][:3]))

    if not bits:
        return "Similar overall playstyle and theme based on its embedding profile."
    if len(bits) == 1:
        return bits[0][0].upper() + bits[0][1:] + "."
    return bits[0][0].upper() + bits[0][1:] + ", " + "; ".join(bits[1:]) + "."
