import argparse
import json
import sqlite3
from typing import List, Tuple

from tqdm import tqdm
from sentence_transformers import SentenceTransformer

from db import db_connection, ensure_schema


def _fetch_profiles_to_embed(conn: sqlite3.Connection, reembed_all: bool) -> List[Tuple[int, str]]:
    if reembed_all:
        sql = "SELECT game_id, profile_text FROM game_profiles ORDER BY game_id"
        cur = conn.execute(sql)
    else:
        sql = """SELECT p.game_id, p.profile_text
                   FROM game_profiles p
                   LEFT JOIN game_embeddings e ON e.game_id = p.game_id
                   WHERE e.game_id IS NULL
                   ORDER BY p.game_id"""
        cur = conn.execute(sql)
    return [(row[0], row[1]) for row in cur.fetchall()]


def main():
    parser = argparse.ArgumentParser(
        description="Create/update embeddings for game profiles (Option B)."
    )
    parser.add_argument("--db", required=True, help="Path to SQLite DB.")
    parser.add_argument(
        "--model-name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence-Transformers model name to use.",
    )
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for embedding.")
    parser.add_argument(
        "--reembed-all",
        type=int,
        default=0,
        help="If 1, re-embed all profiles (overwrite existing embeddings).",
    )

    args = parser.parse_args()
    reembed_all = bool(args.reembed_all)

    print(f"Loading model: {args.model_name}")
    from sentence_transformers import SentenceTransformer  # local import to avoid early import cost
    model = SentenceTransformer(args.model_name)

    with db_connection(args.db) as conn:
        ensure_schema(conn)

        pairs = _fetch_profiles_to_embed(conn, reembed_all=reembed_all)
        if not pairs:
            print("No profiles found that need embeddings.")
            return

        game_ids = [gid for gid, _ in pairs]
        texts = [text for _, text in pairs]

        batch_size = max(1, args.batch_size)

        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding games"):
            batch_ids = game_ids[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]

            embeddings = model.encode(
                batch_texts,
                convert_to_numpy=True,
                batch_size=batch_size,
                show_progress_bar=False,
            )

            for gid, emb in zip(batch_ids, embeddings):
                vec_list = emb.tolist()
                dim = len(vec_list)
                vec_json = json.dumps(vec_list)
                conn.execute(
                    """INSERT INTO game_embeddings (game_id, vector_json, dim, model_name)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(game_id) DO UPDATE SET
                               vector_json = excluded.vector_json,
                               dim = excluded.dim,
                               model_name = excluded.model_name""",
                    (gid, vec_json, dim, args.model_name),
                )


if __name__ == "__main__":
    main()
