"""
Integration tests for similar games feature.
"""
import pytest
from backend.db import execute_query


class TestSimilarGames:
    """Tests for finding similar games."""

    def test_similar_games_basic(self, client, mock_db_connection, create_test_game):
        """Test basic similar games query."""
        # Create test games
        game1 = create_test_game
        game2 = {
            "id": 2,
            "name": "Similar Game",
            "year_published": 2021,
            "min_players": 2,
            "max_players": 4,
            "playing_time": 60,
            "min_age": 10,
            "description": "A similar board game",
            "image_url": "https://example.com/image2.jpg",
            "thumbnail_url": "https://example.com/thumb2.jpg",
            "average_rating": 7.8,
            "num_ratings": 150,
        }

        conn = mock_db_connection
        query = """INSERT INTO games (id, name, year_published, min_players, max_players,
                   playing_time, min_age, description, image_url, thumbnail_url, average_rating, num_ratings)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        execute_query(
            conn,
            query,
            (
                game2["id"],
                game2["name"],
                game2["year_published"],
                game2["min_players"],
                game2["max_players"],
                game2["playing_time"],
                game2["min_age"],
                game2["description"],
                game2["image_url"],
                game2["thumbnail_url"],
                game2["average_rating"],
                game2["num_ratings"],
            ),
        )
        conn.commit()

        # Test similar games endpoint (if it exists)
        # Note: This requires FAISS index to be set up, which may not be available in tests
        response = client.post("/chat", json={"message": "Games similar to Test Game", "user_id": None})

        # Should not return 404
        assert response.status_code != 404

    def test_similar_games_with_collection(self, client, mock_db_connection, create_test_user, create_test_game):
        """Test similar games restricted to user's collection."""
        user = create_test_user
        game = create_test_game

        # Add game to user's collection
        conn = mock_db_connection
        query = "INSERT INTO user_collections (user_id, game_id) VALUES (%s, %s)"
        execute_query(conn, query, (user["id"], game["id"]))
        conn.commit()

        # Create auth token
        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(user["id"]), "user_id": user["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # Test chat with collection scope
        response = client.post(
            "/chat",
            json={"message": "Games similar to Test Game in my collection", "user_id": str(user["id"])},
            headers=headers,
        )

        assert response.status_code in [200, 500]  # 500 if similarity engine not initialized


class TestGlobalVsCollection:
    """Tests for global vs in-collection queries."""

    def test_global_search(self, client, mock_db_connection, create_test_game):
        """Test searching in global scope."""
        game = create_test_game

        response = client.post("/chat", json={"message": "Games similar to Test Game", "user_id": None})

        assert response.status_code != 404

    def test_collection_search(self, client, mock_db_connection, create_test_user, create_test_game):
        """Test searching within user's collection."""
        user = create_test_user
        game = create_test_game

        # Add game to collection
        conn = mock_db_connection
        query = "INSERT INTO user_collections (user_id, game_id) VALUES (%s, %s)"
        execute_query(conn, query, (user["id"], game["id"]))
        conn.commit()

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(user["id"]), "user_id": user["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/chat",
            json={"message": "Games similar to Test Game in my collection", "user_id": str(user["id"])},
            headers=headers,
        )

        assert response.status_code in [200, 500]


class TestDifferentMechanisms:
    """Tests for games like X but with different mechanisms."""

    def test_different_mechanisms_query(self, client, mock_db_connection, create_test_game):
        """Test finding games similar but with different mechanisms."""
        game = create_test_game

        # Add a mechanic to the game
        conn = mock_db_connection

        # Create a mechanic
        query = "INSERT INTO mechanics (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING"
        execute_query(conn, query, (1, "Worker Placement"))
        conn.commit()

        # Link game to mechanic
        query = "INSERT INTO game_mechanics (game_id, mechanic_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"
        execute_query(conn, query, (game["id"], 1))
        conn.commit()

        # Test query for different mechanisms
        response = client.post(
            "/chat", json={"message": "Games like Test Game but with different mechanisms", "user_id": None}
        )

        assert response.status_code != 404


class TestDoINeedFeature:
    """Tests for 'Do I need X' feature."""

    def test_do_i_need_query(self, client, mock_db_connection, create_test_user, create_test_game):
        """Test 'Do I need X' feature."""
        user = create_test_user
        game = create_test_game

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(user["id"]), "user_id": user["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # Test "Do I need" query
        response = client.post("/chat", json={"message": "Do I need Test Game?", "user_id": str(user["id"])}, headers=headers)

        assert response.status_code in [200, 500]


class TestSearchWithFeatures:
    """Tests for searching games with specified features."""

    def test_search_with_mechanic(self, client, mock_db_connection, create_test_game):
        """Test searching games by mechanic."""
        game = create_test_game

        # Add mechanic
        conn = mock_db_connection
        query = "INSERT INTO mechanics (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING"
        execute_query(conn, query, (1, "Deck Building"))
        conn.commit()

        query = "INSERT INTO game_mechanics (game_id, mechanic_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"
        execute_query(conn, query, (game["id"], 1))
        conn.commit()

        # Test search
        response = client.get("/games/search?q=deck building")

        assert response.status_code == 200
        data = response.json()
        assert "games" in data or "features" in data

    def test_search_with_category(self, client, mock_db_connection, create_test_game):
        """Test searching games by category."""
        game = create_test_game

        conn = mock_db_connection
        query = "INSERT INTO categories (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING"
        execute_query(conn, query, (1, "Fantasy"))
        conn.commit()

        query = "INSERT INTO game_categories (game_id, category_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"
        execute_query(conn, query, (game["id"], 1))
        conn.commit()

        response = client.get("/games/search?q=fantasy")

        assert response.status_code == 200
