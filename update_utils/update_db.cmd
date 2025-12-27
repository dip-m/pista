python etl.py --input ./boardgames_ranks.csv --db bgg_semantic.db --limit 30000 --sleep-seconds 5
python build_profiles.py --db bgg_semantic.db
python embed_games.py --db bgg_semantic.db
python export_faiss.py --db bgg_semantic.db --index-out game_vectors.index --id-map-out game_ids.json
python similar_games.py --db bgg_semantic.db --index game_vectors.index --id-map game_ids.json --game-id 224517 --top-k 5 --explain 1
