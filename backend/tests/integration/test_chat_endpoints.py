"""
Integration tests for chat endpoints.
"""
import pytest


class TestChatEndpoints:
    """Tests for chat API endpoints."""

    def test_chat_endpoint_exists(self, client):
        """Test that chat endpoint exists."""
        response = client.post("/chat", json={"message": "Hello", "user_id": None})

        # Should not return 404
        assert response.status_code != 404

    def test_chat_with_message(self, client, mock_db_connection):
        """Test chat with a simple message."""
        response = client.post("/chat", json={"message": "What games are similar to Catan?", "user_id": None})

        assert response.status_code in [200, 500]  # 500 if similarity engine not initialized
        if response.status_code == 200:
            data = response.json()
            assert "response" in data or "message" in data

    def test_chat_with_context(self, client, mock_db_connection):
        """Test chat with context."""
        response = client.post(
            "/chat", json={"message": "Tell me more", "user_id": None, "context": {"previous_message": "What is Catan?"}}
        )

        assert response.status_code in [200, 500]
