"""
Unit tests for database utilities.
"""
import pytest
from backend.db import execute_query


class TestDatabaseOperations:
    """Tests for database operations."""

    def test_execute_query_select(self, test_db):
        """Test executing a SELECT query."""
        # Insert test data
        execute_query(
            test_db,
            "INSERT INTO users (id, email, username, password_hash, oauth_provider) VALUES (%s, %s, %s, %s, %s)",
            (1, "test@example.com", "testuser", "hash", "email"),
        )
        test_db.commit()

        # Query data
        cur = execute_query(test_db, "SELECT * FROM users WHERE email = %s", ("test@example.com",))
        result = cur.fetchall()

        assert result is not None
        assert len(result) == 1
        assert result[0][1] == "test@example.com"  # email is second column

    def test_execute_query_insert(self, test_db):
        """Test executing an INSERT query."""
        execute_query(
            test_db,
            "INSERT INTO users (id, email, username, password_hash, oauth_provider) VALUES (%s, %s, %s, %s, %s)",
            (2, "new@example.com", "newuser", "hash", "email"),
        )
        test_db.commit()

        # Verify insertion
        cur = execute_query(test_db, "SELECT * FROM users WHERE id = %s", (2,))
        result = cur.fetchall()
        assert len(result) == 1
        assert result[0][1] == "new@example.com"  # email is second column

    def test_execute_query_update(self, test_db):
        """Test executing an UPDATE query."""
        # Insert test data
        execute_query(
            test_db,
            "INSERT INTO users (id, email, username, password_hash, oauth_provider) VALUES (%s, %s, %s, %s, %s)",
            (3, "update@example.com", "olduser", "hash", "email"),
        )
        test_db.commit()

        # Update data
        execute_query(test_db, "UPDATE users SET username = %s WHERE id = %s", ("newuser", 3))
        test_db.commit()

        # Verify update
        cur = execute_query(test_db, "SELECT * FROM users WHERE id = %s", (3,))
        result = cur.fetchall()
        assert result[0][2] == "newuser"  # username is third column

    def test_execute_query_delete(self, test_db):
        """Test executing a DELETE query."""
        # Insert test data
        execute_query(
            test_db,
            "INSERT INTO users (id, email, username, password_hash, oauth_provider) VALUES (%s, %s, %s, %s, %s)",
            (4, "delete@example.com", "deleteuser", "hash", "email"),
        )
        test_db.commit()

        # Delete data
        execute_query(test_db, "DELETE FROM users WHERE id = %s", (4,))
        test_db.commit()

        # Verify deletion
        cur = execute_query(test_db, "SELECT * FROM users WHERE id = %s", (4,))
        result = cur.fetchall()
        assert len(result) == 0
