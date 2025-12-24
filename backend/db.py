import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, Any, List, Optional

# Try to import PostgreSQL dependencies
try:
    import psycopg2
    import psycopg2.errors
    from psycopg2 import pool
    from psycopg2.extensions import connection as psycopg2_connection
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None
    psycopg2.errors = None
    psycopg2_connection = None

# Import database configuration
try:
    from backend.config import DB_TYPE, DATABASE_URL
except ImportError:
    # Fallback if config module doesn't exist
    DB_TYPE = os.getenv("DB_TYPE", "sqlite")
    DATABASE_URL = os.getenv("DATABASE_URL", "")

# db.py is now in backend/, so go up one level to reach root
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SCHEMA_FILE = os.path.join(BASE_DIR, "update_utils", "schema.sql")
SCHEMA_FILE_SQLITE = SCHEMA_FILE
SCHEMA_FILE_POSTGRES = os.path.join(BASE_DIR, "update_utils", "schema_postgres.sql")
DB_PATH = os.path.join(BASE_DIR, "gen", "bgg_semantic.db")

# PostgreSQL connection pool (singleton)
_postgres_pool = None

def get_postgres_pool():
    """Get or create PostgreSQL connection pool."""
    global _postgres_pool
    if DB_TYPE != "postgres" or not DATABASE_URL:
        return None
    if not PSYCOPG2_AVAILABLE:
        raise ImportError("psycopg2-binary is required for PostgreSQL support")
    if _postgres_pool is None:
        try:
            _postgres_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL
            )
        except Exception as e:
            raise Exception(f"Failed to create PostgreSQL connection pool: {e}")
    return _postgres_pool

@contextmanager
def db_connection(db_path: str = None):
    """Context manager for database connections. Supports both SQLite and PostgreSQL."""
    if DB_TYPE == "postgres" and DATABASE_URL:
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
    else:
        # SQLite fallback
        path = db_path or DB_PATH
        conn = sqlite3.connect(path, check_same_thread=False)
        if DB_TYPE == "sqlite":
            conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

def get_connection():
    """Get a database connection (for use with SimilarityEngine)."""
    if DB_TYPE == "postgres" and DATABASE_URL:
        pool = get_postgres_pool()
        if pool:
            conn = pool.getconn()
            # Set row factory for compatibility
            return conn
        raise Exception("PostgreSQL connection pool not available")
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

def put_connection(conn):
    """Return a connection to the pool (PostgreSQL) or close it (SQLite)."""
    if DB_TYPE == "postgres":
        pool = get_postgres_pool()
        if pool:
            pool.putconn(conn)
    else:
        conn.close()

def execute_query(conn, query: str, params: tuple = None):
    """Execute a query with proper parameter placeholders."""
    if DB_TYPE == "postgres":
        # Convert ? to %s for PostgreSQL
        query = query.replace("?", "%s")
        cur = conn.cursor()
        try:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur
        except (psycopg2.errors.InFailedSqlTransaction, psycopg2.InterfaceError) as e:
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
    else:
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        return cur


def ensure_schema(conn, schema_path: str = None) -> None:
    """Ensure database schema exists."""
    if schema_path is None:
        schema_path = SCHEMA_FILE_POSTGRES if DB_TYPE == "postgres" else SCHEMA_FILE_SQLITE
    
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    
    # Remove SQLite-specific PRAGMA for PostgreSQL
    if DB_TYPE == "postgres":
        sql = sql.replace("PRAGMA foreign_keys = ON;", "")
        # PostgreSQL requires executing statements one at a time
        # Split by semicolon and execute each statement
        with conn.cursor() as cur:
            # Split SQL into individual statements
            statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
            for statement in statements:
                if statement:  # Skip empty statements
                    try:
                        cur.execute(statement)
                    except Exception as e:
                        # Ignore "already exists" errors
                        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                            raise
        conn.commit()
    else:
        # SQLite: Execute script, but handle errors gracefully for existing tables
        try:
            conn.executescript(sql)
        except sqlite3.OperationalError as e:
            # If error is about missing columns, it's likely a migration issue
            # Log and continue - migration code will handle it
            if "no such column" in str(e).lower():
                logger.warning(f"Schema execution warning (may need migration): {e}")
                # Try to execute statements one by one, skipping problematic ones
                statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
                for statement in statements:
                    if statement:
                        try:
                            conn.execute(statement)
                        except sqlite3.OperationalError as stmt_err:
                            # Skip index creation if columns don't exist yet
                            if "no such column" in str(stmt_err).lower() or "index" in statement.lower():
                                logger.debug(f"Skipping statement (columns may not exist yet): {statement[:50]}...")
                                continue
                            raise
                conn.commit()
            else:
                raise


def upsert_game(conn, game_row: Dict[str, Any]) -> None:
    """Upsert a game record."""
    cols = list(game_row.keys())
    placeholders = ", ".join("?" if DB_TYPE == "sqlite" else "%s" for _ in cols)
    col_list = ", ".join(cols)
    
    if DB_TYPE == "postgres":
        update_assignments = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "id")
        sql = f"""INSERT INTO games ({col_list})
                  VALUES ({placeholders})
                  ON CONFLICT(id) DO UPDATE SET {update_assignments}
               """
    else:
        update_assignments = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "id")
        sql = f"""INSERT INTO games ({col_list})
                  VALUES ({placeholders})
                  ON CONFLICT(id) DO UPDATE SET {update_assignments}
               """
    
    values = [game_row[c] for c in cols]
    execute_query(conn, sql, tuple(values))
    if DB_TYPE == "postgres":
        conn.commit()

def _upsert_vocab(conn, table: str, row_id: int, name: str) -> None:
    """Upsert a vocabulary item (mechanic, category, etc.)."""
    placeholders = "?, ?" if DB_TYPE == "sqlite" else "%s, %s"
    sql = f"""INSERT INTO {table} (id, name)
              VALUES ({placeholders})
              ON CONFLICT(id) DO UPDATE SET name=excluded.name
           """
    execute_query(conn, sql, (row_id, name))
    if DB_TYPE == "postgres":
        conn.commit()

def upsert_links(conn, game_id: int, links_by_type: Dict[str, List[Dict[str, Any]]]) -> None:
    """Upsert game links (mechanics, categories, etc.)."""
    placeholders = "?, ?" if DB_TYPE == "sqlite" else "%s, %s"
    ignore_clause = "OR IGNORE" if DB_TYPE == "sqlite" else "ON CONFLICT DO NOTHING"
    
    for entry in links_by_type.get("boardgamemechanic", []):
        mid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "mechanics", mid, name)
        sql = f"INSERT {ignore_clause} INTO game_mechanics (game_id, mechanic_id) VALUES ({placeholders})"
        execute_query(conn, sql, (game_id, mid))

    for entry in links_by_type.get("boardgamecategory", []):
        cid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "categories", cid, name)
        sql = f"INSERT {ignore_clause} INTO game_categories (game_id, category_id) VALUES ({placeholders})"
        execute_query(conn, sql, (game_id, cid))

    for entry in links_by_type.get("boardgamefamily", []):
        fid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "families", fid, name)
        sql = f"INSERT {ignore_clause} INTO game_families (game_id, family_id) VALUES ({placeholders})"
        execute_query(conn, sql, (game_id, fid))

    for entry in links_by_type.get("boardgamedesigner", []):
        did = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "designers", did, name)
        sql = f"INSERT {ignore_clause} INTO game_designers (game_id, designer_id) VALUES ({placeholders})"
        execute_query(conn, sql, (game_id, did))

    for entry in links_by_type.get("boardgameartist", []):
        aid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "artists", aid, name)
        sql = f"INSERT {ignore_clause} INTO game_artists (game_id, artist_id) VALUES ({placeholders})"
        execute_query(conn, sql, (game_id, aid))

    for entry in links_by_type.get("boardgamepublisher", []):
        pid = entry["id"]
        name = entry["name"]
        _upsert_vocab(conn, "publishers", pid, name)
        sql = f"INSERT {ignore_clause} INTO game_publishers (game_id, publisher_id) VALUES ({placeholders})"
        execute_query(conn, sql, (game_id, pid))
    
    if DB_TYPE == "postgres":
        conn.commit()
