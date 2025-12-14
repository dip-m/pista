import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, Any, List


SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "update_utils", "schema.sql")
DB_PATH = os.path.join(os.path.dirname(__file__), "gen", "bgg_semantic.db")

@contextmanager
def db_connection(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_schema(conn: sqlite3.Connection, schema_path: str = SCHEMA_FILE) -> None:
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)


def upsert_game(conn: sqlite3.Connection, game_row: Dict[str, Any]) -> None:
    cols = list(game_row.keys())
    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(cols)
    update_assignments = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "id")

    sql = f"""INSERT INTO games ({col_list})
              VALUES ({placeholders})
              ON CONFLICT(id) DO UPDATE SET
              {update_assignments}
           """
    values = [game_row[c] for c in cols]
    conn.execute(sql, values)


def _upsert_vocab(conn: sqlite3.Connection, table: str, row_id: int, name: str) -> None:
    sql = f"""INSERT INTO {table} (id, name)
              VALUES (?, ?)
              ON CONFLICT(id) DO UPDATE SET name=excluded.name
           """
    conn.execute(sql, (row_id, name))


def upsert_links(conn: sqlite3.Connection, game_id: int, links_by_type: Dict[str, List[Dict[str, Any]]]) -> None:
    for entry in links_by_type.get("boardgamemechanic", []):
        mid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "mechanics", mid, name)
        conn.execute(
            "INSERT OR IGNORE INTO game_mechanics (game_id, mechanic_id) VALUES (?, ?)",
            (game_id, mid),
        )

    for entry in links_by_type.get("boardgamecategory", []):
        cid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "categories", cid, name)
        conn.execute(
            "INSERT OR IGNORE INTO game_categories (game_id, category_id) VALUES (?, ?)",
            (game_id, cid),
        )

    for entry in links_by_type.get("boardgamefamily", []):
        fid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "families", fid, name)
        conn.execute(
            "INSERT OR IGNORE INTO game_families (game_id, family_id) VALUES (?, ?)",
            (game_id, fid),
        )

    for entry in links_by_type.get("boardgamedesigner", []):
        did = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "designers", did, name)
        conn.execute(
            "INSERT OR IGNORE INTO game_designers (game_id, designer_id) VALUES (?, ?)",
            (game_id, did),
        )

    for entry in links_by_type.get("boardgameartist", []):
        aid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "artists", aid, name)
        conn.execute(
            "INSERT OR IGNORE INTO game_artists (game_id, artist_id) VALUES (?, ?)",
            (game_id, aid),
        )

    for entry in links_by_type.get("boardgamepublisher", []):
        pid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "publishers", pid, name)
        conn.execute(
            "INSERT OR IGNORE INTO game_publishers (game_id, publisher_id) VALUES (?, ?)",
            (game_id, pid),
        )
