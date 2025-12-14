import sqlite3
import json
import os
import re
import os
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "..", "gen/bgg_semantic.db")

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

def get_name_id_map() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.execute("SELECT id, name FROM games")
    rows = cur.fetchall()
    conn.close()

    name_id_map = {}

    for row in rows:
        game_id = row["id"]
        raw_name = row["name"]
        norm_name = normalize_name(raw_name)

        # Basic mapping: full normalized name → id
        # If duplicates exist, you can decide whether to keep first or last.
        if norm_name in name_id_map and name_id_map[norm_name] != game_id:
            # Optional: log conflicts or keep the lower id
            # print(f"Name conflict for {norm_name}: {name_id_map[norm_name]} vs {game_id}")
            pass

        name_id_map[norm_name] = game_id

        # Optional: also add a variant without punctuation
        simple_name = re.sub(r"[^a-z0-9 ]+", "", norm_name)
        simple_name = re.sub(r"\s+", " ", simple_name).strip()
        if simple_name and simple_name != norm_name:
            name_id_map.setdefault(simple_name, game_id)
    return name_id_map


def main():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found at {DB_PATH}")

    name_id_map = get_name_id_map()
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(name_id_map, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(name_id_map)} name→id entries to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

