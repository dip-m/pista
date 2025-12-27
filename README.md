# Pista – BGG Semantic DB + Embeddings (Option B) + Similarity Reasoning

This project builds and maintains a semantic database of board games from
BoardGameGeek XML API2, starting from a boardgames_ranks-style CSV, and then
creates semantic profile texts + embeddings for each game.

New in this version:
- export_faiss.py: export game_embeddings to a FAISS index
- similar_games.py: query similar games using embeddings + explainable metadata overlap

## Pipeline

1. ETL: fetch games by id from BGG and populate SQLite:
   python etl.py --input /path/to/boardgames_ranks.csv --db bgg_semantic.db --sleep-seconds 3

2. Build semantic profiles:
   python build_profiles.py --db bgg_semantic.db

3. Create embeddings:
   python embed_games.py --db bgg_semantic.db

4. Export embeddings to FAISS:
   python export_faiss.py --db bgg_semantic.db --index-out game_vectors.index --id-map-out game_ids.json

5. Query similar games with explanations:
   python similar_games.py --db bgg_semantic.db --index game_vectors.index --id-map game_ids.json --game-id 224517 --top-k 10 --explain 1

## Documentation

All project documentation is located in the [`docs/`](docs/) folder, including:
- Deployment guides
- Testing documentation
- Migration guides
- Environment setup instructions
- And more...

See [`docs/README.md`](docs/README.md) for a complete list of available documentation.
