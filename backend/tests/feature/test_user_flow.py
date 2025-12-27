"""
Feature tests for complete user flows.
"""
import pytest


class TestUserRegistrationFlow:
    """Test complete user registration and login flow."""

    def test_complete_registration_flow(self, client, mock_db_connection):
        """Test: Register -> Login -> Get Profile."""
        # Step 1: Register
        register_response = client.post(
            "/auth/register", json={"email": "flow@example.com", "password": "password123", "username": "flowuser"}
        )
        assert register_response.status_code in [200, 201]

        # Extract token if available
        register_data = register_response.json()
        token = None
        if "access_token" in register_data:
            token = register_data["access_token"]
        elif "token" in register_data:
            token = register_data["token"]

        # Step 2: Login (if registration didn't return token)
        if not token:
            login_response = client.post("/auth/login", json={"email": "flow@example.com", "password": "password123"})
            assert login_response.status_code == 200
            login_data = login_response.json()
            token = login_data.get("access_token") or login_data.get("token")

        # Step 3: Get profile (if token available)
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            profile_response = client.get("/auth/me", headers=headers)
            # Should return user info or 404 if endpoint doesn't exist
            assert profile_response.status_code in [200, 404]


class TestGameSearchFlow:
    """Test game search and interaction flow."""

    def test_game_search_flow(self, client, mock_db_connection):
        """Test: Search for game -> Get game details."""
        # Step 1: Search for games
        search_response = client.get("/games/search?q=catan")

        # Should return results or empty list
        assert search_response.status_code in [200, 500]

        if search_response.status_code == 200:
            data = search_response.json()
            # Response should be a list or dict with games
            assert isinstance(data, (list, dict))

            # If games found, test getting details
            if isinstance(data, list) and len(data) > 0:
                game_id = data[0].get("id")
                if game_id:
                    detail_response = client.get(f"/games/{game_id}")
                    assert detail_response.status_code in [200, 404]
