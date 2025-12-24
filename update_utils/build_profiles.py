import argparse
import sqlite3
from typing import List

from tqdm import tqdm

from backend.db import db_connection, ensure_schema


def _fetch_one_game(conn: sqlite3.Connection, game_id: int):
    cur = conn.execute(
        """SELECT id, name, description, year_published, min_players, max_players,
                      playing_time, min_playtime, max_playtime, min_age, avg_weight
               FROM games WHERE id = ?""",
        (game_id,),
    )
    return cur.fetchone()


def _fetch_names(conn: sqlite3.Connection, sql: str, game_id: int) -> List[str]:
    cur = conn.execute(sql, (game_id,))
    return [row[0] for row in cur.fetchall()]


def build_profile_text(conn: sqlite3.Connection, game_id: int) -> str:
    row = _fetch_one_game(conn, game_id)
    if row is None:
        return ""

    (
        _id,
        name,
        description,
        year,
        min_players,
        max_players,
        playing_time,
        min_playtime,
        max_playtime,
        min_age,
        avg_weight,
    ) = row

    mechanics = _fetch_names(
        conn,
        """SELECT m.name
               FROM mechanics m
               JOIN game_mechanics gm ON gm.mechanic_id = m.id
               WHERE gm.game_id = ?
               ORDER BY m.name""",
        game_id,
    )

    categories = _fetch_names(
        conn,
        """SELECT c.name
               FROM categories c
               JOIN game_categories gc ON gc.category_id = c.id
               WHERE gc.game_id = ?
               ORDER BY c.name""",
        game_id,
    )

    families = _fetch_names(
        conn,
        """SELECT f.name
               FROM families f
               JOIN game_families gf ON gf.family_id = f.id
               WHERE gf.game_id = ?
               ORDER BY f.name""",
        game_id,
    )

    designers = _fetch_names(
        conn,
        """SELECT d.name
               FROM designers d
               JOIN game_designers gd ON gd.designer_id = d.id
               WHERE gd.game_id = ?
               ORDER BY d.name""",
        game_id,
    )

    artists = _fetch_names(
        conn,
        """SELECT a.name
               FROM artists a
               JOIN game_artists ga ON ga.artist_id = a.id
               WHERE ga.game_id = ?
               ORDER BY a.name""",
        game_id,
    )

    publishers = _fetch_names(
        conn,
        """SELECT p.name
               FROM publishers p
               JOIN game_publishers gp ON gp.publisher_id = p.id
               WHERE gp.game_id = ?
               ORDER BY p.name""",
        game_id,
    )

    lines = []

    if name:
        lines.append(f"Name: {name}")

    meta_parts = []
    if year:
        meta_parts.append(f"Year: {year}")
    if min_players and max_players:
        meta_parts.append(f"Players: {min_players}–{max_players}")
    elif min_players or max_players:
        meta_parts.append(f"Players: {min_players or max_players}")
    if min_playtime and max_playtime:
        meta_parts.append(f"Playtime: {min_playtime}–{max_playtime} minutes")
    elif playing_time:
        meta_parts.append(f"Playtime: {playing_time} minutes")
    if min_age:
        meta_parts.append(f"Age: {min_age}+")
    if avg_weight:
        meta_parts.append(f"Weight: {round(avg_weight, 2)}")

    if meta_parts:
        lines.append(" / ".join(meta_parts))

    if description:
        lines.append(f"Description: {description.strip()}")

    if mechanics:
        lines.append("Mechanics: " + ", ".join(mechanics))
    if categories:
        lines.append("Categories: " + ", ".join(categories))
    if families:
        lines.append("Families: " + ", ".join(families))
    if designers:
        lines.append("Designers: " + ", ".join(designers))
    if artists:
        lines.append("Artists: " + ", ".join(artists))
    if publishers:
        lines.append("Publishers: " + ", ".join(publishers))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Build semantic profile texts for games (for embeddings)."
    )
    parser.add_argument("--db", required=True, help="Path to SQLite DB.")
    parser.add_argument(
        "--rebuild-all",
        type=int,
        default=0,
        help="If 1, rebuild profiles for all games; else only missing profiles.",
    )
    args = parser.parse_args()
    rebuild_all = bool(args.rebuild_all)

    with db_connection(args.db) as conn:
        ensure_schema(conn)

        if rebuild_all:
            cur = conn.execute("SELECT id FROM games ORDER BY id")
        else:
            cur = conn.execute(
                """SELECT g.id
                       FROM games g
                       LEFT JOIN game_profiles p ON p.game_id = g.id
                       WHERE p.game_id IS NULL
                       ORDER BY g.id"""
            )

        game_ids = [row[0] for row in cur.fetchall()]
        if not game_ids:
            print("No games found that need profiles.")
            return

        for gid in tqdm(game_ids, desc="Building profiles"):
            text = build_profile_text(conn, gid)
            if not text:
                continue
            conn.execute(
                """INSERT INTO game_profiles (game_id, profile_text)
                       VALUES (?, ?)
                       ON CONFLICT(game_id) DO UPDATE SET
                           profile_text = excluded.profile_text""",
                (gid, text),
            )


if __name__ == "__main__":
    main()
