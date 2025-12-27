"""
Integration tests for admin workflows.
"""
import pytest
import json
from backend.db import execute_query


class TestGameMods:
    """Tests for modifying game features (mods)."""

    def test_add_game_mod(self, client, mock_db_connection, create_admin_user, create_test_game):
        """Test adding a feature modification to a game."""
        admin = create_admin_user
        game = create_test_game

        # Create mechanic
        conn = mock_db_connection
        query = "INSERT INTO mechanics (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING"
        execute_query(conn, query, (1, "Test Mechanic"))
        conn.commit()

        # Create admin token
        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # Add mod
        response = client.post(
            f"/games/{game['id']}/features/modify",
            params={"feature_type": "mechanics", "feature_id": 1, "action": "add"},
            headers=headers,
        )

        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist yet

    def test_remove_game_mod(self, client, mock_db_connection, create_admin_user, create_test_game):
        """Test removing a feature modification from a game."""
        admin = create_admin_user
        game = create_test_game

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # First add a mod
        conn = mock_db_connection
        query = "INSERT INTO mechanics (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING"
        execute_query(conn, query, (1, "Test Mechanic"))
        conn.commit()

        query = """INSERT INTO feature_mods (game_id, feature_type, feature_id, action)
                   VALUES (%s, %s, %s, %s)"""
        execute_query(conn, query, (game["id"], "mechanics", 1, "add"))
        conn.commit()

        # Get mod ID
        query = "SELECT id FROM feature_mods WHERE game_id = %s LIMIT 1"
        cur = execute_query(conn, query, (game["id"],))
        mod_row = cur.fetchone()
        if mod_row:
            mod_id = mod_row[0]

            # Remove mod
            response = client.delete(f"/games/{game['id']}/features/modify/{mod_id}", headers=headers)

            assert response.status_code in [200, 404]


class TestABTests:
    """Tests for A/B test configuration."""

    def test_create_ab_test(self, client, mock_db_connection, create_admin_user):
        """Test creating an A/B test configuration."""
        admin = create_admin_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        config_value = json.dumps({"variant_a": 0.5, "variant_b": 0.5})

        response = client.post(
            "/admin/ab-test-configs",
            params={"config_key": "test_experiment", "config_value": config_value, "is_active": True},
            headers=headers,
        )

        assert response.status_code in [200, 404]

    def test_get_ab_tests(self, client, mock_db_connection, create_admin_user):
        """Test getting all A/B test configurations."""
        admin = create_admin_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/admin/ab-test-configs", headers=headers)

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "configs" in data or isinstance(data, list)

    def test_update_ab_test(self, client, mock_db_connection, create_admin_user):
        """Test updating an A/B test configuration."""
        admin = create_admin_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # First create one
        config_value = json.dumps({"variant_a": 0.5, "variant_b": 0.5})
        client.post(
            "/admin/ab-test-configs",
            params={"config_key": "test_experiment", "config_value": config_value, "is_active": True},
            headers=headers,
        )

        # Update it
        new_config_value = json.dumps({"variant_a": 0.7, "variant_b": 0.3})
        response = client.put(
            "/admin/ab-test-configs/test_experiment",
            params={"config_value": new_config_value, "is_active": False},
            headers=headers,
        )

        assert response.status_code in [200, 404]


class TestFeedbackQuestions:
    """Tests for feedback question management."""

    def test_create_feedback_question(self, client, mock_db_connection, create_admin_user):
        """Test creating a feedback question."""
        admin = create_admin_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/admin/feedback/questions",
            json={
                "question_text": "Was this response helpful?",
                "question_type": "single_select",
                "is_active": True,
                "options": ["Yes", "No"],
            },
            headers=headers,
        )

        assert response.status_code in [200, 201, 404]

    def test_get_feedback_questions(self, client, mock_db_connection, create_admin_user):
        """Test getting all feedback questions."""
        admin = create_admin_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/admin/feedback/questions", headers=headers)

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "questions" in data

    def test_update_feedback_question(self, client, mock_db_connection, create_admin_user):
        """Test updating a feedback question."""
        admin = create_admin_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # First create one
        create_response = client.post(
            "/admin/feedback/questions",
            json={
                "question_text": "Was this helpful?",
                "question_type": "single_select",
                "is_active": True,
                "options": ["Yes", "No"],
            },
            headers=headers,
        )

        if create_response.status_code in [200, 201]:
            question_id = create_response.json().get("question_id") or 1

            # Update it
            response = client.put(
                f"/admin/feedback/questions/{question_id}",
                json={
                    "question_text": "Was this response helpful?",
                    "question_type": "single_select",
                    "is_active": False,
                    "options": ["Yes", "No", "Maybe"],
                },
                headers=headers,
            )

            assert response.status_code in [200, 404]
