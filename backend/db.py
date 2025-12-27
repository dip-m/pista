"""
Database connection and query utilities - PostgreSQL only.
"""
import os
from contextlib import contextmanager
from typing import Dict, Any, List

# PostgreSQL dependencies (required)
try:
    import psycopg2
    import psycopg2.errors
    from psycopg2 import pool

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    raise ImportError("psycopg2-binary is required. Install with: pip install psycopg2-binary")

# Import database configuration
try:
    from backend.config import DATABASE_URL
except ImportError:
    # Fallback if config module doesn't exist
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required for PostgreSQL")

# db.py is now in backend/, so go up one level to reach root
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SCHEMA_FILE_POSTGRES = os.path.join(BASE_DIR, "update_utils", "schema_postgres.sql")

# PostgreSQL connection pool (singleton)
_postgres_pool = None


def get_postgres_pool():
    """Get or create PostgreSQL connection pool."""
    global _postgres_pool
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is required for PostgreSQL")
    if not PSYCOPG2_AVAILABLE:
        raise ImportError("psycopg2-binary is required for PostgreSQL support")
    if _postgres_pool is None:
        try:
            _postgres_pool = pool.SimpleConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
        except Exception as e:
            raise Exception(f"Failed to create PostgreSQL connection pool: {e}")
    return _postgres_pool


@contextmanager
def db_connection():
    """Context manager for PostgreSQL database connections."""
    pool = get_postgres_pool()
    if pool:
        conn = pool.getconn()
        try:
            yield conn
            conn.commit()
        finally:
            pool.putconn(conn)
    else:
        raise Exception("PostgreSQL connection pool not available")


def get_connection():
    """Get a database connection (for use with SimilarityEngine)."""
    pool = get_postgres_pool()
    if pool:
        conn = pool.getconn()
        return conn
    raise Exception("PostgreSQL connection pool not available")


def put_connection(conn):
    """Return a connection to the pool."""
    pool = get_postgres_pool()
    if pool:
        pool.putconn(conn)


def get_db_connection():
    """
    Get a database connection for request handling.
    Gets a connection from the PostgreSQL pool.
    This should be used as a FastAPI dependency.
    """
    if not PSYCOPG2_AVAILABLE:
        raise Exception("psycopg2 is required for PostgreSQL")
    pool = get_postgres_pool()
    if pool:
        conn = pool.getconn()
        try:
            # Test if connection is still alive
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return conn
        except (psycopg2.InterfaceError, psycopg2.OperationalError):
            # Connection is dead, get a new one
            try:
                pool.putconn(conn, close=True)
            except Exception:
                pass
            return pool.getconn()
    raise Exception("PostgreSQL connection pool not available")


def execute_query(conn, query: str, params: tuple = None):
    """Execute a query with PostgreSQL parameter placeholders (%s)."""
    # Ensure query uses %s placeholders for PostgreSQL
    query = query.replace("?", "%s")
    cur = conn.cursor()
    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        return cur
    except (psycopg2.errors.InFailedSqlTransaction, psycopg2.InterfaceError):
        # Transaction is in failed state, rollback and retry
        try:
            conn.rollback()
            # Retry the query after rollback
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur
        except Exception as retry_error:
            # If retry also fails, rollback and re-raise
            conn.rollback()
            raise retry_error


def ensure_schema(conn, schema_path: str = None) -> None:
    """Ensure database schema exists."""
    if schema_path is None:
        schema_path = SCHEMA_FILE_POSTGRES

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # PostgreSQL requires executing statements one at a time
    # Split by semicolon and execute each statement
    with conn.cursor() as cur:
        # Split SQL into individual statements
        statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
        for statement in statements:
            if statement:  # Skip empty statements
                try:
                    cur.execute(statement)
                except Exception as e:
                    # Ignore "already exists" errors
                    if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                        raise
    conn.commit()


def upsert_game(conn, game_row: Dict[str, Any]) -> None:
    """Upsert a game record."""
    cols = list(game_row.keys())
    placeholders = ", ".join("%s" for _ in cols)
    col_list = ", ".join(cols)

    update_assignments = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "id")
    sql = f"""INSERT INTO games ({col_list})
              VALUES ({placeholders})
              ON CONFLICT(id) DO UPDATE SET {update_assignments}
           """

    values = [game_row[c] for c in cols]
    execute_query(conn, sql, tuple(values))
    conn.commit()


def _upsert_vocab(conn, table: str, row_id: int, name: str) -> None:
    """Upsert a vocabulary item (mechanic, category, etc.)."""
    sql = f"""INSERT INTO {table} (id, name)
              VALUES (%s, %s)
              ON CONFLICT(id) DO UPDATE SET name=excluded.name
           """
    execute_query(conn, sql, (row_id, name))
    conn.commit()


def upsert_links(conn, game_id: int, links_by_type: Dict[str, List[Dict[str, Any]]]) -> None:
    """Upsert game links (mechanics, categories, etc.)."""
    ignore_clause = "ON CONFLICT DO NOTHING"

    for entry in links_by_type.get("boardgamemechanic", []):
        mid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "mechanics", mid, name)
        sql = f"INSERT {ignore_clause} INTO game_mechanics (game_id, mechanic_id) VALUES (%s, %s)"
        execute_query(conn, sql, (game_id, mid))

    for entry in links_by_type.get("boardgamecategory", []):
        cid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "categories", cid, name)
        sql = f"INSERT {ignore_clause} INTO game_categories (game_id, category_id) VALUES (%s, %s)"
        execute_query(conn, sql, (game_id, cid))

    for entry in links_by_type.get("boardgamefamily", []):
        fid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "families", fid, name)
        sql = f"INSERT {ignore_clause} INTO game_families (game_id, family_id) VALUES (%s, %s)"
        execute_query(conn, sql, (game_id, fid))

    for entry in links_by_type.get("boardgamedesigner", []):
        did = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "designers", did, name)
        sql = f"INSERT {ignore_clause} INTO game_designers (game_id, designer_id) VALUES (%s, %s)"
        execute_query(conn, sql, (game_id, did))

    for entry in links_by_type.get("boardgameartist", []):
        aid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "artists", aid, name)
        sql = f"INSERT {ignore_clause} INTO game_artists (game_id, artist_id) VALUES (%s, %s)"
        execute_query(conn, sql, (game_id, aid))

    for entry in links_by_type.get("boardgamepublisher", []):
        pid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "publishers", pid, name)
        sql = f"INSERT {ignore_clause} INTO game_publishers (game_id, publisher_id) VALUES (%s, %s)"
        execute_query(conn, sql, (game_id, pid))

    conn.commit()
