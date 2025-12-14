# similar_games.py
import argparse
import json
import sqlite3

import faiss

from db import db_connection, ensure_schema
from backend.similarity_engine import SimilarityEngine


def _load_index(path: str):
    return faiss.read_index(path)


def _load_id_map(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(...)
    # existing args...
    parser.add_argument("--constraints-json", help="JSON string with constraint config.")
    parser.add_argument("--use-collection-file", help="Path to JSON array of allowed_ids (for testing).")
    args = parser.parse_args()

    constraints = json.loads(args.constraints_json) if args.constraints_json else {}
    allowed_ids = None
    if args.use_collection_file:
        with open(args.use_collection_file, "r", encoding="utf-8") as f:
            allowed_ids = set(json.load(f))

    index = _load_index(args.index)
    id_map = _load_id_map(args.id_map)

    with db_connection(args.db) as conn:
        ensure_schema(conn)
        engine = SimilarityEngine(conn, index, id_map)

        results = engine.search_similar(
            game_id=args.game_id,
            top_k=args.top_k,
            include_self=bool(args.include_self),
            constraints=constraints,
            allowed_ids=allowed_ids,
            explain=bool(args.explain),
        )

    print(json.dumps(results, ensure_ascii=False, indent=2))
