import sqlite3, json, numpy as np, re, faiss
from embeddings import embed  # your embedding function

conn = sqlite3.connect("pista_semantic.db")
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT id, name, description FROM games").fetchall()
conn.close()

game_ids = []
name_id_map = {}
vectors = []

def normalize(text):
    text = text.lower().strip()
    return re.sub(r"\s+", " ", text)

for row in rows:
    gid = row["id"]
    name = row["name"]
    text = f"{name}. {row['description'] or ''}"

    vec = embed(text)              # 768-dim or whatever model returns
    vectors.append(vec)
    game_ids.append(gid)
    name_id_map[normalize(name)] = gid

vectors = np.array(vectors, dtype="float32")
faiss.normalize_L2(vectors)

index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)

faiss.write_index(index, "game_index.faiss")

with open("game_ids.json", "w", encoding="utf-8") as f:
    json.dump(game_ids, f)

with open("name_id_map.json", "w", encoding="utf-8") as f:
    json.dump(name_id_map, f, ensure_ascii=False, indent=2)

print(f"? Saved {len(game_ids)} embeddings, index, and name map.")
