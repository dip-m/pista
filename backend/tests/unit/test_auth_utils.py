"""
Unit tests for authentication utilities.
"""
import pytest
from backend.auth_utils import hash_password, verify_password, create_access_token, decode_access_token


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hash_result = hash_password(password)

        assert hash_result is not None
        assert isinstance(hash_result, str)
        # SHA-256 format: {salt}:{hash}
        assert ":" in hash_result
        salt, hash_part = hash_result.split(":", 1)
        assert len(salt) == 32  # 16 bytes hex = 32 chars
        assert len(hash_part) == 64  # SHA-256 hex = 64 chars

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hash_result = hash_password(password)

        assert verify_password(password, hash_result) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        hash_result = hash_password(password)

        assert verify_password("wrongpassword", hash_result) is False

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWT:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "test@example.com", "user_id": 1}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """Test JWT token decoding."""
        data = {"sub": "test@example.com", "user_id": 1}
        token = create_access_token(data)

        decoded = decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == "test@example.com"
        assert decoded["user_id"] == 1

    def test_decode_invalid_token(self):
        """Test decoding invalid token."""
        invalid_token = "invalid.token.here"

        decoded = decode_access_token(invalid_token)
        assert decoded is None
