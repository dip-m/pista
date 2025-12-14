import sqlite3
from typing import Dict, Set, List, Tuple


def _fetch_name(conn: sqlite3.Connection, game_id: int) -> str:
    cur = conn.execute("SELECT name FROM games WHERE id = ?", (game_id,))
    row = cur.fetchone()
    return row[0] if row else ""


def _fetch_feature_names(
    conn: sqlite3.Connection,
    join_table: str,
    vocab_table: str,
    join_col_game: str,
    join_col_vocab: str,
) -> Set[str]:
    sql = f"""SELECT v.name
               FROM {vocab_table} v
               JOIN {join_table} j ON j.{join_col_vocab} = v.id
               WHERE j.{join_col_game} = ?
               ORDER BY v.name"""
    cur = conn.execute(sql, (game_id,))
    return {row[0] for row in cur.fetchall()}


def get_game_features(conn: sqlite3.Connection, game_id: int) -> Dict[str, object]:
    name = _fetch_name(conn, game_id)

    def fetch(join_table, vocab_table, join_vocab_col):
        sql = f"""SELECT v.name
                   FROM {vocab_table} v
                   JOIN {join_table} j ON j.{join_vocab_col} = v.id
                   WHERE j.game_id = ?
                   ORDER BY v.name"""
        cur = conn.execute(sql, (game_id,))
        return {row[0] for row in cur.fetchall()}

    mechanics = fetch("game_mechanics", "mechanics", "mechanic_id")
    categories = fetch("game_categories", "categories", "category_id")
    families = fetch("game_families", "families", "family_id")
    designers = fetch("game_designers", "designers", "designer_id")
    artists = fetch("game_artists", "artists", "artist_id")
    publishers = fetch("game_publishers", "publishers", "publisher_id")

    return {
        "id": game_id,
        "name": name,
        "mechanics": mechanics,
        "categories": categories,
        "families": families,
        "designers": designers,
        "artists": artists,
        "publishers": publishers,
    }


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union) if union else 0.0


def compute_meta_similarity(f1: Dict[str, object], f2: Dict[str, object]) -> Tuple[float, Dict[str, List[str]], Dict[str, float]]:
    mech1, mech2 = f1["mechanics"], f2["mechanics"]
    cat1, cat2 = f1["categories"], f2["categories"]
    fam1, fam2 = f1["families"], f2["families"]
    des1, des2 = f1["designers"], f2["designers"]
    art1, art2 = f1["artists"], f2["artists"]
    pub1, pub2 = f1["publishers"], f2["publishers"]

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

    meta_score = (
        0.35 * scores["j_mechanics"]
        + 0.25 * scores["j_categories"]
        + 0.15 * scores["j_families"]
        + 0.10 * scores["j_designers"]
        + 0.05 * scores["j_artists"]
        + 0.10 * scores["j_publishers"]
    )

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
    return (bits[0][0].upper() + bits[0][1:] + ", " + "; ".join(bits[1:]) + ".")
