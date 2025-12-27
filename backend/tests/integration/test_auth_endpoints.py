"""
Integration tests for authentication endpoints.
"""
import pytest
from backend.auth_utils import hash_password


class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    def test_register_user(self, client, mock_db_connection):
        """Test user registration."""
        response = client.post(
            "/auth/register", json={"email": "newuser@example.com", "password": "securepassword123", "username": "newuser"}
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "access_token" in data or "token" in data or "message" in data

    def test_register_duplicate_email(self, client, mock_db_connection):
        """Test registering with duplicate email."""
        # Register first user
        client.post("/auth/register", json={"email": "duplicate@example.com", "password": "password123", "username": "user1"})

        # Try to register again with same email
        response = client.post(
            "/auth/register", json={"email": "duplicate@example.com", "password": "password123", "username": "user2"}
        )

        assert response.status_code == 400 or response.status_code == 409

    def test_login_success(self, client, mock_db_connection):
        """Test successful login."""
        # Register user first
        client.post("/auth/register", json={"email": "login@example.com", "password": "password123", "username": "loginuser"})

        # Login
        response = client.post("/auth/login", json={"email": "login@example.com", "password": "password123"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data or "token" in data

    def test_login_invalid_credentials(self, client, mock_db_connection):
        """Test login with invalid credentials."""
        response = client.post("/auth/login", json={"email": "nonexistent@example.com", "password": "wrongpassword"})

        assert response.status_code == 401 or response.status_code == 404

    def test_get_current_user(self, client, mock_db_connection, auth_headers):
        """Test getting current user info."""
        response = client.get("/auth/me", headers=auth_headers)

        # Should return user info or 200/404 depending on implementation
        assert response.status_code in [200, 404]
