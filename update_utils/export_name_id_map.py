import json
import os
import re
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
OUTPUT_JSON = os.path.join(BASE_DIR, "..", "name_id_map.json")


def normalize_name(name: str) -> str:
    """
    Normalize a game name for fuzzy matching:
    - lowercase
    - strip leading/trailing spaces
    - collapse multiple spaces
    """
    name = name.lower().strip()
    # replace sequences of whitespace with single space
    name = re.sub(r"\s+", " ", name)
    return name

def get_name_id_map(conn=None) -> dict:
    """
    Get name-to-id mapping from database.
    Works with both SQLite and PostgreSQL.
    
    Args:
        conn: Database connection (optional). If None, will try to get from backend.db
    """
    # Try to use provided connection or get from backend
    if conn is None:
        try:
            from backend.db import get_connection, put_connection, DB_TYPE
            conn = get_connection()
            should_close = True
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            # Fallback to SQLite if backend.db not available
            import sqlite3
            DB_PATH = os.path.join(BASE_DIR, "..", "gen/bgg_semantic.db")
            if not os.path.exists(DB_PATH):
                raise FileNotFoundError(f"Database not found and cannot get connection: {e}")
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            should_close = True
    else:
        should_close = False
    
    try:
        # Use execute_query if available (for PostgreSQL compatibility)
        try:
            from backend.db import execute_query
            cur = execute_query(conn, "SELECT id, name FROM games")
            rows = cur.fetchall()
        except ImportError:
            # Fallback to direct execute
            cur = conn.execute("SELECT id, name FROM games")
            rows = cur.fetchall()
        
        name_id_map = {}

        for row in rows:
            # Handle both SQLite Row objects and PostgreSQL tuples
            if hasattr(row, 'keys'):
                # SQLite Row or PostgreSQL dict-like
                game_id = row[0] if isinstance(row, tuple) else row['id']
                raw_name = row[1] if isinstance(row, tuple) else row['name']
            else:
                # Tuple
                game_id = row[0]
                raw_name = row[1]
            
            norm_name = normalize_name(raw_name)

            # Basic mapping: full normalized name → id
            # If duplicates exist, you can decide whether to keep first or last.
            if norm_name in name_id_map and name_id_map[norm_name] != game_id:
                # Optional: log conflicts or keep the lower id
                # logger.debug(f"Name conflict for {norm_name}: {name_id_map[norm_name]} vs {game_id}")
                pass

            name_id_map[norm_name] = game_id

            # Optional: also add a variant without punctuation
            simple_name = re.sub(r"[^a-z0-9 ]+", "", norm_name)
            simple_name = re.sub(r"\s+", " ", simple_name).strip()
            if simple_name and simple_name != norm_name:
                name_id_map.setdefault(simple_name, game_id)
        
        return name_id_map
    finally:
        if should_close:
            try:
                from backend.db import put_connection
                put_connection(conn)
            except:
                try:
                    conn.close()
                except:
                    pass


def main():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found at {DB_PATH}")

    name_id_map = get_name_id_map()
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(name_id_map, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(name_id_map)} name→id entries to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

