"""
Pytest configuration and fixtures for backend tests - PostgreSQL only.
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Generator

# Disable langsmith plugin to avoid compatibility issues
try:
    import pytest_plugins

    if hasattr(pytest_plugins, "langsmith"):
        delattr(pytest_plugins, "langsmith")
except Exception:
    pass

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables before imports
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pista_test")
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://test.local"

# Import after setting env vars
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import get_db_connection, put_connection, ensure_schema, DATABASE_URL, get_postgres_pool

# Test database name
TEST_DB_NAME = "pista_test"


@pytest.fixture(scope="session")
def test_db_setup():
    """Create test database if it doesn't exist."""
    # Connect to postgres database to create test database
    base_url = DATABASE_URL.rsplit("/", 1)[0]  # Remove database name
    try:
        conn = psycopg2.connect(base_url + "/postgres", connect_timeout=5)
    except (psycopg2.OperationalError, psycopg2.Error) as e:
        pytest.skip(f"Could not connect to PostgreSQL: {e}. Skipping database tests.")

    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Check if test database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,))
        exists = cur.fetchone()

        if not exists:
            cur.execute(f"CREATE DATABASE {TEST_DB_NAME}")
            print(f"Created test database: {TEST_DB_NAME}")

        cur.close()
        conn.close()

        yield

        # Cleanup: drop test database (optional - comment out to keep test data)
        # conn = psycopg2.connect(base_url + '/postgres')
        # conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        # cur = conn.cursor()
        # cur.execute(f'DROP DATABASE IF EXISTS {TEST_DB_NAME}')
        # cur.close()
        # conn.close()
    except Exception as e:
        conn.close()
        pytest.skip(f"Database setup failed: {e}. Skipping database tests.")


@pytest.fixture(scope="function")
def test_db(test_db_setup):
    """Create a fresh test database connection for each test."""
    try:
        # Get connection from pool
        pool = get_postgres_pool()
        if pool is None:
            pytest.skip("PostgreSQL connection pool not available. Skipping database tests.")

        conn = pool.getconn()
        if conn is None:
            pytest.skip("Could not get database connection. Skipping database tests.")

        # Ensure schema
        schema_path = Path(__file__).parent.parent.parent / "update_utils" / "schema_postgres.sql"
        ensure_schema(conn, str(schema_path))

        # Clean up data before test
        cur = conn.cursor()
        # Get all table names
        cur.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename NOT LIKE 'pg_%'
        """
        )
        tables = [row[0] for row in cur.fetchall()]

        # Truncate all tables (cascade to handle foreign keys)
        for table in tables:
            try:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            except Exception:
                pass

        conn.commit()
        cur.close()

        yield conn

        # Clean up after test
        cur = conn.cursor()
        for table in tables:
            try:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            except Exception:
                pass
        conn.commit()
        cur.close()

        # Return connection to pool
        put_connection(conn)
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}. Skipping database tests.")


@pytest.fixture(scope="function")
def mock_db_connection(test_db, monkeypatch):
    """Mock database connection to use test database."""

    def get_test_connection():
        return test_db

    monkeypatch.setattr("backend.db.get_db_connection", get_test_connection)
    monkeypatch.setattr("backend.main.ENGINE_CONN", test_db)

    yield test_db


@pytest.fixture(scope="function")
def client(mock_db_connection):
    """Create a test client for FastAPI."""
    return TestClient(app)


@pytest.fixture(scope="function")
def auth_headers():
    """Create authentication headers for testing."""
    from backend.auth_utils import create_access_token

    token = create_access_token({"sub": "1", "user_id": 1})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_headers():
    """Create admin authentication headers for testing."""
    from backend.auth_utils import create_access_token

    token = create_access_token({"sub": "999", "user_id": 999})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def sample_game_data():
    """Sample game data for testing."""
    return {
        "id": 1,
        "name": "Test Game",
        "year_published": 2020,
        "min_players": 2,
        "max_players": 4,
        "playing_time": 60,
        "min_age": 10,
        "description": "A test board game",
        "image_url": "https://example.com/image.jpg",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "average_rating": 7.5,
        "num_ratings": 100,
    }


@pytest.fixture(scope="function")
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y5Y",  # "testpass"
        "oauth_provider": "email",
    }


@pytest.fixture(scope="function")
def create_test_user(mock_db_connection, sample_user_data):
    """Create a test user in the database."""
    from backend.db import execute_query
    from backend.auth_utils import hash_password

    conn = mock_db_connection
    user_data = sample_user_data.copy()

    # Calculate next ID for PostgreSQL
    cur = execute_query(conn, "SELECT COALESCE(MAX(id), 0) + 1 FROM users")
    next_id = cur.fetchone()[0]
    user_data["id"] = next_id

    query = """INSERT INTO users (id, email, username, password_hash, oauth_provider, is_admin)
               VALUES (%s, %s, %s, %s, %s, %s)"""
    execute_query(
        conn,
        query,
        (
            user_data["id"],
            user_data["email"],
            user_data["username"],
            user_data["password_hash"],
            user_data["oauth_provider"],
            False,
        ),
    )
    conn.commit()

    return user_data


@pytest.fixture(scope="function")
def create_test_game(mock_db_connection, sample_game_data):
    """Create a test game in the database."""
    from backend.db import execute_query

    conn = mock_db_connection
    game_data = sample_game_data.copy()

    query = """INSERT INTO games (id, name, year_published, min_players, max_players,
               playing_time, min_age, description, image_url, thumbnail_url, average_rating, num_ratings)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET
               name = EXCLUDED.name,
               year_published = EXCLUDED.year_published"""
    execute_query(
        conn,
        query,
        (
            game_data["id"],
            game_data["name"],
            game_data["year_published"],
            game_data["min_players"],
            game_data["max_players"],
            game_data["playing_time"],
            game_data["min_age"],
            game_data["description"],
            game_data["image_url"],
            game_data["thumbnail_url"],
            game_data["average_rating"],
            game_data["num_ratings"],
        ),
    )
    conn.commit()

    return game_data


@pytest.fixture(scope="function")
def create_admin_user(mock_db_connection):
    """Create an admin user for testing."""
    from backend.db import execute_query
    from backend.auth_utils import hash_password

    conn = mock_db_connection

    cur = execute_query(conn, "SELECT COALESCE(MAX(id), 0) + 1 FROM users")
    admin_id = cur.fetchone()[0]

    password_hash = hash_password("adminpass")
    query = """INSERT INTO users (id, email, username, password_hash, oauth_provider, is_admin)
               VALUES (%s, %s, %s, %s, %s, %s)"""
    execute_query(conn, query, (admin_id, "admin@example.com", "admin", password_hash, "email", True))
    conn.commit()

    return {"id": admin_id, "email": "admin@example.com", "username": "admin", "is_admin": True}
