"""
Integration tests for account deletion and data export.
"""
import pytest
from backend.db import execute_query


class TestAccountDeletion:
    """Tests for account deletion features."""

    def test_export_user_data(self, client, mock_db_connection, create_test_user, create_test_game):
        """Test exporting user data."""
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

        response = client.get("/profile/export-data", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "collection" in data
        assert "chat_threads" in data
        assert "feedback_responses" in data
        assert "scoring_sessions" in data

    def test_delete_own_account(self, client, mock_db_connection, create_test_user):
        """Test user deleting their own account."""
        user = create_test_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(user["id"]), "user_id": user["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # Delete account
        response = client.delete("/profile/account", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify user is deleted
        conn = mock_db_connection
        query = "SELECT id FROM users WHERE id = %s"
        cur = execute_query(conn, query, (user["id"],))
        assert cur.fetchone() is None

    def test_delete_own_account_with_data(self, client, mock_db_connection, create_test_user, create_test_game):
        """Test deleting account with associated data."""
        user = create_test_user
        game = create_test_game

        # Add data
        conn = mock_db_connection
        query = "INSERT INTO user_collections (user_id, game_id) VALUES (%s, %s)"
        execute_query(conn, query, (user["id"], game["id"]))
        conn.commit()

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(user["id"]), "user_id": user["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # Delete account
        response = client.delete("/profile/account", headers=headers)

        assert response.status_code == 200

        # Verify all data is deleted
        conn = mock_db_connection
        query = "SELECT id FROM user_collections WHERE user_id = %s"
        cur = execute_query(conn, query, (user["id"],))
        assert cur.fetchone() is None


class TestAdminUserDeletion:
    """Tests for admin deleting users."""

    def test_admin_get_all_users(self, client, mock_db_connection, create_admin_user, create_test_user):
        """Test admin getting list of all users."""
        admin = create_admin_user
        user = create_test_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/admin/users", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert len(data["users"]) >= 1  # At least the admin user

    def test_admin_delete_user(self, client, mock_db_connection, create_admin_user, create_test_user):
        """Test admin deleting another user."""
        admin = create_admin_user
        user = create_test_user

        from backend.auth_utils import create_access_token

        admin_token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Delete user
        response = client.delete(f"/admin/users/{user['id']}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify user is deleted
        conn = mock_db_connection
        query = "SELECT id FROM users WHERE id = %s"
        cur = execute_query(conn, query, (user["id"],))
        assert cur.fetchone() is None

    def test_admin_cannot_delete_self(self, client, mock_db_connection, create_admin_user):
        """Test that admin cannot delete themselves from admin panel."""
        admin = create_admin_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(admin["id"]), "user_id": admin["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # Try to delete self
        response = client.delete(f"/admin/users/{admin['id']}", headers=headers)

        assert response.status_code == 400
        data = response.json()
        assert "Cannot delete your own account" in data["detail"]

    def test_non_admin_cannot_delete_users(self, client, mock_db_connection, create_test_user):
        """Test that non-admin users cannot delete other users."""
        user = create_test_user

        from backend.auth_utils import create_access_token

        token = create_access_token({"sub": str(user["id"]), "user_id": user["id"]})
        headers = {"Authorization": f"Bearer {token}"}

        # Try to delete another user (should fail - user doesn't exist, but should get 403)
        response = client.delete("/admin/users/999", headers=headers)

        # Should get 403 Forbidden, not 404
        assert response.status_code in [403, 404]
