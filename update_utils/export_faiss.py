import argparse
import json
import sqlite3

import numpy as np
import faiss

from backend.db import db_connection, ensure_schema


def main():
    parser = argparse.ArgumentParser(description="Export game_embeddings to a FAISS index.")
    parser.add_argument("--db", required=True, help="Path to SQLite DB.")
    parser.add_argument("--index-out", required=True, help="Path to write FAISS index file.")
    parser.add_argument("--id-map-out", required=True, help="Path to write JSON list of game_ids.")
    args = parser.parse_args()

    with db_connection(args.db) as conn:
        ensure_schema(conn)
        cur = conn.execute(
            "SELECT game_id, vector_json FROM game_embeddings ORDER BY game_id"
        )
        rows = cur.fetchall()

    if not rows:
        print("No embeddings found in game_embeddings.")
        return

    game_ids = []
    vectors = []
    for gid, vjson in rows:
        try:
            vec = np.array(json.loads(vjson), dtype="float32")
        except Exception:
            continue
        game_ids.append(gid)
        vectors.append(vec)

    if not vectors:
        print("No valid vectors parsed from game_embeddings.")
        return

    mat = np.stack(vectors, axis=0)

    # Normalize for cosine similarity via inner product
    faiss.normalize_L2(mat)

    dim = mat.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(mat)

    faiss.write_index(index, args.index_out)

    with open(args.id_map_out, "w", encoding="utf-8") as f:
        json.dump(game_ids, f, ensure_ascii=False)

    print(f"Wrote index with {len(game_ids)} vectors (dim={dim}) to {args.index_out}")
    print(f"Wrote id map to {args.id_map_out}")


if __name__ == "__main__":
    main()
