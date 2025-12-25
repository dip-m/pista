# backend/app/main.py
from typing import Dict, Any, Optional, Set, List, Union
import json
import sqlite3
from datetime import datetime

# Try to import psycopg2 for type hints
try:
    import psycopg2
    from psycopg2.extensions import connection as psycopg2_connection
except ImportError:
    psycopg2 = None
    psycopg2_connection = None

import faiss
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .db import db_connection, DB_PATH, ensure_schema, DB_TYPE, DATABASE_URL, get_connection, put_connection, execute_query, get_db_connection
# Import psycopg2 errors for PostgreSQL error handling
try:
    import psycopg2
    import psycopg2.errors
except ImportError:
    psycopg2 = None

from backend.chat_nlu import interpret_message
from backend.similarity_engine import SimilarityEngine
from fastapi.middleware.cors import CORSMiddleware
from update_utils.export_name_id_map import get_name_id_map
from backend.reasoning_utils import get_game_features, compute_meta_similarity, build_reason_summary
from backend.auth_utils import (
    hash_password, verify_password, create_access_token, decode_access_token,
    verify_google_token, verify_microsoft_token, verify_meta_token
)
from backend.logger_config import logger
from backend.bgg_collection import fetch_user_collection
from backend.image_processing import analyze_image, generate_prompt_from_analysis, generate_image
from backend.cache import get_cached, set_cached

import os
# BASE_DIR is now one level up since main.py is in backend/
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
index_path = os.path.join(BASE_DIR, "gen", "game_vectors.index")
SCHEMA_FILE = os.path.join(BASE_DIR, "update_utils", "schema.sql")
SCHEMA_FILE_POSTGRES = os.path.join(BASE_DIR, "update_utils", "schema_postgres.sql")


app = FastAPI(title="Pista Service")
security = HTTPBearer(auto_error=False)  # Make auth optional

# Import configuration
try:
    from backend.config import ALLOWED_ORIGINS
except ImportError:
    # Fallback if config module doesn't exist
    import os
    ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://pistatabletop.netlify.app")
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Globals for demo; for production you'd handle lifecycle more carefully.
ENGINE: Optional[SimilarityEngine] = None
if psycopg2_connection:
    ENGINE_CONN: Optional[Union[sqlite3.Connection, psycopg2_connection]] = None
else:
    ENGINE_CONN: Optional[sqlite3.Connection] = None


class ChatRequest(BaseModel):
    user_id: Optional[str] = None  # Optional for anonymous users
    message: str
    context: Optional[Dict[str, Any]] = None
    thread_id: Optional[int] = None
    selected_game_id: Optional[int] = None  # Game selected from search, bypasses NLU


class FeedbackQuestionRequest(BaseModel):
    question_text: str
    question_type: str
    is_active: bool = True
    options: Optional[List[str]] = None


class FeedbackResponseRequest(BaseModel):
    question_id: Optional[int] = None
    option_id: Optional[int] = None
    response: Optional[str] = None
    context: Optional[str] = None
    thread_id: Optional[int] = None
    additional_details: Optional[str] = None  # Optional text for "No" or dislike responses


class ChatResponse(BaseModel):
    reply_text: str
    results: Optional[List[Dict[str, Any]]] = None
    query_spec: Optional[Dict[str, Any]] = None
    thread_id: Optional[int] = None
    ab_responses: Optional[List[Dict[str, Any]]] = None


class UsernameUpdateRequest(BaseModel):
    username: str

class BggIdUpdateRequest(BaseModel):
    bgg_id: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    provider: str  # 'google', 'microsoft', 'meta'
    token: str
    email: Optional[str] = None
    name: Optional[str] = None


class EmailLoginRequest(BaseModel):
    email: str
    password: str


class EmailRegisterRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: Optional[str] = None
    username: Optional[str] = None
    bgg_id: Optional[str] = None
    is_admin: bool = False
    
    class Config:
        # Allow string values for bgg_id even if database returns different type
        json_encoders = {
            str: str
        }


class GameSearchResult(BaseModel):
    id: int
    name: str
    year_published: Optional[int] = None
    thumbnail: Optional[str] = None


class CollectionGame(BaseModel):
    game_id: int
    name: str
    year_published: Optional[int] = None
    thumbnail: Optional[str] = None
    added_at: str


class ChatThread(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: str
    updated_at: str


class ChatMessage(BaseModel):
    id: int
    role: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


def load_id_map(path: str) -> List[int]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current user from JWT token. Returns None if not authenticated."""
    if credentials is None:
        return None
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        if payload is None:
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        # Verify user exists - use execute_query for compatibility
        query = "SELECT id, email, username, bgg_id, is_admin FROM users WHERE id = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (int(user_id),))
        user = cur.fetchone()
        if user is None:
            return None
        
        # Handle both SQLite Row and PostgreSQL tuple
        if hasattr(user, 'keys'):
            # SQLite Row
            return {
                "id": user[0], 
                "email": user[1] if len(user) > 1 else None,
                "username": user[2] if len(user) > 2 else None,
                "bgg_id": user[3] if len(user) > 3 else None,
                "is_admin": bool(user[4] if len(user) > 4 else 0)
            }
        else:
            # PostgreSQL tuple
            return {
                "id": user[0], 
                "email": user[1] if len(user) > 1 else None,
                "username": user[2] if len(user) > 2 else None,
                "bgg_id": user[3] if len(user) > 3 else None,
                "is_admin": bool(user[4] if len(user) > 4 else False)
            }
    except Exception as e:
        logger.debug(f"Error getting current user: {e}", exc_info=True)
        return None


def get_current_user_required(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token. Raises exception if not authenticated."""
    user = get_current_user(credentials)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def get_current_admin_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """Get current admin user from JWT token. Raises exception if not authenticated or not admin."""
    user = get_current_user_required(credentials)
    # Check if user is admin in database (token might be stale)
    query = "SELECT is_admin FROM users WHERE id = ?"
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    cur = execute_query(ENGINE_CONN, query, (user["id"],))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    is_admin = row[0] if isinstance(row[0], bool) else bool(row[0])
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def load_user_collection(user_id: str) -> Set[int]:
    """Load user's collection BGG IDs from database."""
    if not ENGINE_CONN:
        return set()
    try:
        query = "SELECT game_id FROM user_collections WHERE user_id = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (int(user_id),))
        return {row[0] for row in cur.fetchall()}
    except (ValueError, sqlite3.Error):
        return set()
    except Exception as e:
        # Handle PostgreSQL errors if psycopg2 is available
        if psycopg2 and hasattr(psycopg2, 'Error') and isinstance(e, psycopg2.Error):
            return set()
        raise


@app.on_event("startup")
def on_startup() -> None:
    global ENGINE, ENGINE_CONN
    try:
        logger.info("Starting Pista service...")
        
        # Initialize database connection
        if DB_TYPE == "postgres" and DATABASE_URL:
            logger.info("Connecting to PostgreSQL database...")
            try:
                ENGINE_CONN = get_connection()
                SCHEMA_FILE_POSTGRES = os.path.join(BASE_DIR, "update_utils", "schema_postgres.sql")
                ensure_schema(ENGINE_CONN, SCHEMA_FILE_POSTGRES)
                logger.info("PostgreSQL schema ensured")
            except Exception as db_err:
                raise
        else:
            logger.info("Connecting to SQLite database...")
            try:
                ENGINE_CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
                ENGINE_CONN.row_factory = sqlite3.Row
            except Exception as db_err:
                raise
        
        # Run migration FIRST for SQLite (before ensure_schema)
        # This ensures old databases are migrated before schema is applied
        # Only run SQLite-specific migration code if using SQLite
        # CRITICAL: Re-check DB_TYPE from environment at runtime to ensure it's correct
        # The module-level DB_TYPE might have been set to "sqlite" at import time
        # before environment variables were loaded
        runtime_db_type = os.getenv("DB_TYPE", DB_TYPE)
        if runtime_db_type == "sqlite":
            try:
                # Check if users table exists (SQLite-specific query)
                cur = execute_query(ENGINE_CONN, "SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                table_exists = cur.fetchone() is not None
                
                if table_exists:
                    cur = execute_query(ENGINE_CONN, "PRAGMA table_info(users)")
                    columns = {row[1]: row[2] for row in cur.fetchall()}
                else:
                    columns = {}  # Table doesn't exist, will be created by ensure_schema
                
                # Migrate to OAuth-compatible schema if needed
                needs_oauth_migration = 'email' not in columns or 'oauth_provider' not in columns
                migration_completed = False
                
                if needs_oauth_migration and table_exists:
                    logger.info("Migrating users table to OAuth-compatible schema")
                    
                    # Clean up any leftover users_new table from previous failed migration
                    cur = execute_query(ENGINE_CONN, "SELECT name FROM sqlite_master WHERE type='table' AND name='users_new'")
                    if cur.fetchone():
                        logger.info("Cleaning up leftover users_new table from previous migration")
                        execute_query(ENGINE_CONN, "DROP TABLE IF EXISTS users_new")
                        ENGINE_CONN.commit()
                
                # Create new table with OAuth columns
                execute_query(ENGINE_CONN, """
                    CREATE TABLE users_new (
                        id             INTEGER PRIMARY KEY AUTOINCREMENT,
                        email          TEXT UNIQUE,
                        username       TEXT,
                        oauth_provider TEXT,
                        oauth_id       TEXT,
                        password_hash  TEXT,
                        bgg_id         TEXT,
                        is_admin       INTEGER DEFAULT 0,
                        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create unique index for OAuth provider/id combination
                execute_query(ENGINE_CONN, """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_users_oauth_unique 
                    ON users_new(oauth_provider, oauth_id) 
                    WHERE oauth_provider IS NOT NULL AND oauth_id IS NOT NULL
                """)
                
                # Migrate existing users to email provider
                # Check if we have old-style users (username, password_hash, no email)
                if 'username' in columns and 'password_hash' in columns:
                    logger.info("Migrating existing users to email-based auth")
                    execute_query(ENGINE_CONN, """
                        INSERT INTO users_new (id, email, username, oauth_provider, password_hash, bgg_id, is_admin, created_at)
                        SELECT 
                            id,
                            CASE 
                                WHEN username LIKE '%@%' THEN username 
                                ELSE username || '@migrated.local' 
                            END as email,
                            username,
                            'email' as oauth_provider,
                            password_hash,
                            bgg_id,
                            COALESCE(is_admin, 0) as is_admin,
                            COALESCE(created_at, CURRENT_TIMESTAMP) as created_at
                        FROM users
                    """)
                else:
                    # Table exists but might be empty or partially migrated
                    logger.info("Users table structure updated, no data to migrate")
                
                # Drop old table and rename new one
                execute_query(ENGINE_CONN, "DROP TABLE IF EXISTS users")
                execute_query(ENGINE_CONN, "ALTER TABLE users_new RENAME TO users")
                ENGINE_CONN.commit()
                logger.info("OAuth migration complete")
                
                # Re-fetch columns to verify migration
                cur = execute_query(ENGINE_CONN, "PRAGMA table_info(users)")
                columns = {row[1]: row[2] for row in cur.fetchall()}
                logger.info(f"Migration verified. Users table now has columns: {list(columns.keys())}")
                migration_completed = True
                
                # Add individual columns if missing (for incremental updates)
                # Only if full migration didn't run
                if table_exists and not migration_completed and 'email' not in columns:
                    logger.info("Adding email column to users table")
                    execute_query(ENGINE_CONN, "ALTER TABLE users ADD COLUMN email TEXT")
                    ENGINE_CONN.commit()
                
                if table_exists and not migration_completed and 'oauth_provider' not in columns:
                    logger.info("Adding oauth_provider column to users table")
                    execute_query(ENGINE_CONN, "ALTER TABLE users ADD COLUMN oauth_provider TEXT")
                    ENGINE_CONN.commit()
                
                if table_exists and not migration_completed and 'oauth_id' not in columns:
                    logger.info("Adding oauth_id column to users table")
                    execute_query(ENGINE_CONN, "ALTER TABLE users ADD COLUMN oauth_id TEXT")
                    ENGINE_CONN.commit()
                
                # Migrate bgg_id column from INTEGER to TEXT if needed
                if 'bgg_id' in columns and columns['bgg_id'].upper() == 'INTEGER':
                    logger.info("Migrating bgg_id column from INTEGER to TEXT")
                    logger.warning("bgg_id is INTEGER, should be TEXT. Consider running full migration.")
                
                # Add is_admin column if it doesn't exist
                if 'is_admin' not in columns:
                    logger.info("Adding is_admin column to users table")
                    execute_query(ENGINE_CONN, "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
                    ENGINE_CONN.commit()
                    
            except sqlite3.Error as e:
                error_msg = str(e)
                logger.error(f"Migration failed: {e}", exc_info=True)
                # If migration failed, try to verify current state
                try:
                    cur = execute_query(ENGINE_CONN, "SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                    if cur.fetchone():
                        cur = execute_query(ENGINE_CONN, "PRAGMA table_info(users)")
                        columns = {row[1]: row[2] for row in cur.fetchall()}
                        if 'email' not in columns:
                            logger.error("CRITICAL: Users table exists but missing email column. Migration must be completed manually.")
                            logger.error("You may need to manually run the migration or recreate the database.")
                        else:
                            logger.info("Migration appears to have completed despite error message")
                except Exception as verify_err:
                    logger.error(f"Could not verify migration state: {verify_err}")
            
            # Now run ensure_schema after migration (SQLite only)
            ensure_schema(ENGINE_CONN, SCHEMA_FILE)
            logger.info("SQLite schema ensured")
            
            # Final verification: Ensure OAuth columns exist
            try:
                cur = execute_query(ENGINE_CONN, "SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if cur.fetchone():
                    cur = execute_query(ENGINE_CONN, "PRAGMA table_info(users)")
                    final_columns = {row[1]: row[2] for row in cur.fetchall()}
                    if 'email' not in final_columns or 'oauth_provider' not in final_columns:
                        logger.error("CRITICAL: OAuth migration incomplete. Users table missing required columns.")
                        logger.error("Please run: python update_utils/fix_sqlite_oauth_schema.py --db-path gen/bgg_semantic.db")
                        raise RuntimeError("Database schema migration incomplete. Cannot start server.")
                    else:
                        logger.info("✅ OAuth schema verification passed")
            except RuntimeError:
                raise  # Re-raise the critical error
            except Exception as verify_err:
                logger.warning(f"Could not verify final schema state: {verify_err}")

        # Load FAISS index and initialize similarity engine
        try:
            index = faiss.read_index(index_path)
            id_map = load_id_map(os.path.join(BASE_DIR, "gen", "game_ids.json"))
            ENGINE = SimilarityEngine(ENGINE_CONN, index, id_map)
            logger.info(f"SimilarityEngine initialized with {len(id_map)} games")
        except Exception as e:
            logger.error(f"Failed to initialize SimilarityEngine: {e}")
            ENGINE = None
    except Exception as startup_err:
        logger.error(f"Startup failed: {startup_err}", exc_info=True)
        raise


@app.on_event("shutdown")
def on_shutdown() -> None:
    global ENGINE_CONN
    if ENGINE_CONN is not None:
        if DB_TYPE == "postgres":
            put_connection(ENGINE_CONN)
        else:
            ENGINE_CONN.close()
        ENGINE_CONN = None


def search_by_features_only(
    required_feature_values: Optional[Dict[str, Set[str]]] = None,
    include_features: Optional[List[str]] = None,
    exclude_features: Optional[List[str]] = None,
    constraints: Optional[Dict[str, Any]] = None,
    allowed_ids: Optional[Set[int]] = None,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """Search games by features only, ordered by rating."""
    try:
        constraints = constraints or {}
        required_feature_values = required_feature_values or {}
        
        # Build SQL query to find games with required features
        # Start with base query
        joins = []
        conditions = []
        params = []
        
        # Add joins and conditions for each required feature type
        # For each feature type, we need to ensure the game has ALL required values
        for feature_type, required_values in required_feature_values.items():
            if not required_values:
                continue
            
            # For each required value, we need a separate condition to ensure ALL are present
            # Use a subquery or multiple EXISTS clauses
            feature_conditions = []
            for req_value in required_values:
                if feature_type == "mechanics":
                    feature_conditions.append("""EXISTS (
                        SELECT 1 FROM game_mechanics gm2 
                        JOIN mechanics m2 ON m2.id = gm2.mechanic_id 
                        WHERE gm2.game_id = g.id AND LOWER(m2.name) = LOWER(?)
                    )""")
                    params.append(req_value)
                elif feature_type == "categories":
                    feature_conditions.append("""EXISTS (
                        SELECT 1 FROM game_categories gc2 
                        JOIN categories c2 ON c2.id = gc2.category_id 
                        WHERE gc2.game_id = g.id AND LOWER(c2.name) = LOWER(?)
                    )""")
                    params.append(req_value)
                elif feature_type == "designers":
                    feature_conditions.append("""EXISTS (
                        SELECT 1 FROM game_designers gd2 
                        JOIN designers d2 ON d2.id = gd2.designer_id 
                        WHERE gd2.game_id = g.id AND LOWER(d2.name) = LOWER(?)
                    )""")
                    params.append(req_value)
                elif feature_type == "families":
                    feature_conditions.append("""EXISTS (
                        SELECT 1 FROM game_families gf2 
                        JOIN families f2 ON f2.id = gf2.family_id 
                        WHERE gf2.game_id = g.id AND LOWER(f2.name) = LOWER(?)
                    )""")
                    params.append(req_value)
            
            if feature_conditions:
                conditions.append("(" + " AND ".join(feature_conditions) + ")")
        
        # Build final query
        if not conditions:
            # No required features - just return top rated games
            sql = """SELECT DISTINCT g.id, g.name, g.year_published, g.thumbnail, 
                            g.average_rating, g.num_ratings, g.min_players, g.max_players, g.description
                     FROM games g"""
            if allowed_ids and len(allowed_ids) > 0:
                placeholders = ",".join(["?" for _ in allowed_ids])
                sql += f" WHERE g.id IN ({placeholders})"
                params.extend(list(allowed_ids))
            sql += " ORDER BY g.num_ratings DESC NULLS LAST, g.average_rating DESC NULLS LAST LIMIT ?"
            params.append(top_k)
        else:
            # Has required features
            sql = f"""SELECT DISTINCT g.id, g.name, g.year_published, g.thumbnail, 
                            g.average_rating, g.num_ratings, g.min_players, g.max_players, g.description
                     FROM games g
                     WHERE {' AND '.join(conditions)}"""
            if allowed_ids and len(allowed_ids) > 0:
                placeholders = ",".join(["?" for _ in allowed_ids])
                sql += f" AND g.id IN ({placeholders})"
                params.extend(list(allowed_ids))
            sql += " ORDER BY g.num_ratings DESC NULLS LAST, g.average_rating DESC NULLS LAST LIMIT ?"
            params.append(top_k)
        
        logger.debug(f"Feature-only search SQL: {sql[:200]}... with {len(params)} params")
        try:
            cur = execute_query(ENGINE_CONN, sql, tuple(params) if params else None)
        except Exception as e:
            logger.error(f"SQL error in feature-only search: {e}, SQL: {sql}, params: {params}")
            return []
        results = []
        for row in cur.fetchall():
            game_id = row[0]
            # Get all features for this game
            from backend.reasoning_utils import get_game_features
            try:
                game_features = get_game_features(ENGINE_CONN, game_id)
            except Exception as e:
                logger.warning(f"Error getting features for game {game_id}: {e}")
                game_features = {}
            
            # Get designers for this game
            designers = []
            try:
                cur_d = execute_query(
                    ENGINE_CONN,
                    """SELECT d.name FROM designers d
                       JOIN game_designers gd ON gd.designer_id = d.id
                       WHERE gd.game_id = ? ORDER BY d.name""",
                    (game_id,)
                )
                designers = [r[0] for r in cur_d.fetchall()]
            except Exception:
                pass
            
            # Row structure: id, name, year_published, thumbnail, average_rating, num_ratings, min_players, max_players, description
            # Get all features as lists (not sets) for JSON serialization
            all_mechanics = list(game_features.get("mechanics", []))
            all_categories = list(game_features.get("categories", []))
            all_designers = list(game_features.get("designers", []))
            all_families = list(game_features.get("families", []))
            
            results.append({
                "game_id": game_id,
                "name": row[1],
                "year_published": row[2],
                "thumbnail": row[3],
                "average_rating": row[4],
                "num_ratings": row[5],
                "min_players": row[6],
                "max_players": row[7],
                "description": row[8] if len(row) > 8 and row[8] else None,
                "designers": designers,  # Keep for backward compatibility
                # Return all features (not shared) for feature-only search
                "mechanics": all_mechanics,
                "categories": all_categories,
                "designers_list": all_designers,  # Use designers_list to distinguish from designers (which is already used for display)
                "families": all_families,
                "reason_summary": "Found by matching required features"
            })
        
        logger.info(f"Feature-only search returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Error in feature-only search: {e}", exc_info=True)
        return []


def compare_two_games(engine: SimilarityEngine, game_a_id: Any, game_b_id: Any) -> Dict[str, Any]:
    """
    Very simple pairwise comparison using the same feature logic.
    """
    conn = engine.conn
    fa = get_game_features(conn, game_a_id)
    fb = get_game_features(conn, game_b_id)

    meta_score, overlaps, scores = compute_meta_similarity(fa, fb)

    # rough natural language reason
    reason = build_reason_summary(fa, overlaps)

    return {
        "game_a_id": game_a_id,
        "game_b_id": game_b_id,
        "meta_score": meta_score,
        "overlaps": overlaps,
        "scores": scores,
        "reason_summary": reason,
    }


@app.post("/auth/oauth/callback")
def oauth_callback(req: OAuthCallbackRequest):
    """Handle OAuth callback from Google, Microsoft, or Meta."""
    # Get a fresh connection from the pool for this request
    conn = get_db_connection()
    try:
        if req.provider not in ["google", "microsoft", "meta"]:
            raise HTTPException(status_code=400, detail="Invalid OAuth provider")
        
        # Verify token and get user info
        user_info = None
        if req.provider == "google":
            user_info = verify_google_token(req.token)
        elif req.provider == "microsoft":
            user_info = verify_microsoft_token(req.token)
        elif req.provider == "meta":
            user_info = verify_meta_token(req.token)
        
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid OAuth token")
        
        oauth_id = user_info.get("oauth_id")
        email = user_info.get("email") or req.email
        username = user_info.get("username") or req.name or email
        
        if not oauth_id:
            raise HTTPException(status_code=400, detail="OAuth ID not found")
        
        # Check if user exists
        query = "SELECT id, email, username, is_admin FROM users WHERE oauth_provider = ? AND oauth_id = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(conn, query, (req.provider, oauth_id))
        user = cur.fetchone()
        
        is_new_user = False
        if user:
            # Existing user - login
            user_id = user[0]
            is_admin = user[3] if len(user) > 3 else False
            if isinstance(is_admin, int):
                is_admin = bool(is_admin)
        else:
            # New user - create account (username is NULL initially, user will set it in profile)
            is_new_user = True
            if DB_TYPE == "postgres":
                # Get next ID for PostgreSQL (since id is INTEGER PRIMARY KEY, not SERIAL)
                id_query = "SELECT COALESCE(MAX(id), 0) + 1 FROM users"
                cur = execute_query(conn, id_query)
                next_id = cur.fetchone()[0]
                
                insert_query = """INSERT INTO users (id, email, username, oauth_provider, oauth_id) 
                                 VALUES (%s, %s, %s, %s, %s) RETURNING id"""
                cur = execute_query(conn, insert_query, (next_id, email, None, req.provider, oauth_id))
                user_id = cur.fetchone()[0]
            else:
                insert_query = """INSERT INTO users (email, username, oauth_provider, oauth_id) 
                                 VALUES (?, ?, ?, ?)"""
                cur = execute_query(conn, insert_query, (email, None, req.provider, oauth_id))
                user_id = cur.lastrowid
            conn.commit()
            is_admin = False
        
        access_token = create_access_token(data={"sub": str(user_id)})
        return {"access_token": access_token, "token_type": "bearer", "user_id": user_id, "is_new_user": is_new_user}
    finally:
        # Return connection to pool if PostgreSQL
        if DB_TYPE == "postgres":
            put_connection(conn)


@app.post("/auth/email/register")
def email_register(req: EmailRegisterRequest):
    """Register a new user with email (restricted to email provider only)."""
    # Get a fresh connection from the pool for this request
    conn = get_db_connection()
    try:
        # Check if email exists
        query = "SELECT id FROM users WHERE email = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(conn, query, (req.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create user with email provider - username is NULL initially, user will set it in profile
        password_hash = hash_password(req.password)
        if DB_TYPE == "postgres":
            # Get next ID for PostgreSQL (since id is INTEGER PRIMARY KEY, not SERIAL)
            id_query = "SELECT COALESCE(MAX(id), 0) + 1 FROM users"
            cur = execute_query(conn, id_query)
            next_id = cur.fetchone()[0]
            
            insert_query = """INSERT INTO users (id, email, username, oauth_provider, password_hash) 
                             VALUES (%s, %s, %s, 'email', %s) RETURNING id"""
            cur = execute_query(conn, insert_query, (next_id, req.email, None, password_hash))
            user_id = cur.fetchone()[0]
        else:
            insert_query = """INSERT INTO users (email, username, oauth_provider, password_hash) 
                             VALUES (?, ?, 'email', ?)"""
            cur = execute_query(conn, insert_query, (req.email, None, password_hash))
            user_id = cur.lastrowid
        
        conn.commit()
        
        access_token = create_access_token(data={"sub": str(user_id)})
        return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}
    finally:
        # Return connection to pool if PostgreSQL
        if DB_TYPE == "postgres":
            put_connection(conn)


@app.post("/auth/email/login")
def email_login(req: EmailLoginRequest):
    """Login with email and password."""
    # Get a fresh connection from the pool for this request
    conn = get_db_connection()
    try:
        query = "SELECT id, password_hash, bgg_id, is_admin FROM users WHERE email = ? AND oauth_provider = 'email'"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(conn, query, (req.email,))
        user = cur.fetchone()
        
        if not user or not verify_password(req.password, user[1]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        access_token = create_access_token(data={"sub": str(user[0])})
        return {"access_token": access_token, "token_type": "bearer", "user_id": user[0]}
    finally:
        # Return connection to pool if PostgreSQL
        if DB_TYPE == "postgres":
            put_connection(conn)


@app.get("/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get current user information."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    # Ensure bgg_id is a string or None
    bgg_id = current_user.get("bgg_id")
    if bgg_id is not None:
        bgg_id = str(bgg_id)  # Convert to string if it's not already
    # Ensure is_admin is included
    if "is_admin" not in current_user:
        query = "SELECT is_admin FROM users WHERE id = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (current_user["id"],))
        row = cur.fetchone()
        current_user["is_admin"] = bool(row[0] if row else False)
    return UserResponse(
        id=current_user["id"],
        email=current_user.get("email"),
        username=current_user.get("username"),
        bgg_id=bgg_id,
        is_admin=current_user.get("is_admin", False)
    )


@app.put("/profile/username")
def update_username(req: UsernameUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Update user's username."""
    # Validate and sanitize input
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    
    # Check if username is already taken
    query = "SELECT id FROM users WHERE username = ? AND id != ?"
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    cur = execute_query(ENGINE_CONN, query, (username, current_user["id"]))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    logger.info(f"Updating username for user {current_user['id']} to {username}")
    query = "UPDATE users SET username = ? WHERE id = ?"
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    execute_query(ENGINE_CONN, query, (username, current_user["id"]))
    ENGINE_CONN.commit()
    
    logger.info(f"Username updated successfully for user {current_user['id']}")
    return {"success": True, "username": username}


@app.put("/profile/bgg-id")
def update_bgg_id(req: BggIdUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Update user's BGG ID (can be text/username or numeric ID)."""
    # Validate and sanitize input
    bgg_id = req.bgg_id
    if bgg_id:
        bgg_id = bgg_id.strip()
        if not bgg_id:
            bgg_id = None
    else:
        bgg_id = None
    
    logger.info(f"Updating BGG ID for user {current_user['id']} to {bgg_id}")
    query = "UPDATE users SET bgg_id = ? WHERE id = ?"
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    execute_query(ENGINE_CONN, query, (bgg_id, current_user["id"]))
    ENGINE_CONN.commit()
    
    logger.info(f"BGG ID updated successfully for user {current_user['id']}")
    return {"success": True, "bgg_id": bgg_id}


@app.post("/profile/collection/import-bgg")
def import_bgg_collection(current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Import collection from BGG."""
    bgg_id_value = current_user.get("bgg_id")
    if not bgg_id_value:
        raise HTTPException(status_code=400, detail="BGG ID not set. Please set your BGG ID first.")
    
    logger.info(f"Importing BGG collection for user {current_user['id']} (BGG ID: {current_user['bgg_id']})")
    
    try:
        # Ensure personal_rating column exists (SQLite only)
        if DB_TYPE == "sqlite":
            try:
                cur = execute_query(ENGINE_CONN, "PRAGMA table_info(user_collections)")
                columns = [row[1] for row in cur.fetchall()]
                if "personal_rating" not in columns:
                    execute_query(ENGINE_CONN, "ALTER TABLE user_collections ADD COLUMN personal_rating REAL")
                    ENGINE_CONN.commit()
                    logger.info("Added personal_rating column to user_collections table")
            except sqlite3.Error as e:
                logger.warning(f"Error checking/adding personal_rating column: {e}")
        
        games_data = fetch_user_collection(str(current_user["bgg_id"]))
        logger.info(f"Fetched {len(games_data)} games from BGG")
        
        # Verify games exist in our DB and add to collection
        added_count = 0
        skipped_count = 0
        updated_count = 0
        
        for game_data in games_data:
            game_id = game_data["game_id"]
            personal_rating = game_data.get("personal_rating")
            
            # Check if game exists in DB
            query = "SELECT id FROM games WHERE id = ?"
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
            cur = execute_query(ENGINE_CONN, query, (game_id,))
            if not cur.fetchone():
                logger.debug(f"Game {game_id} not found in local DB, skipping")
                skipped_count += 1
                continue
            
            # Check if already in collection
            query = "SELECT personal_rating FROM user_collections WHERE user_id = ? AND game_id = ?"
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
            cur = execute_query(ENGINE_CONN, query, (current_user["id"], game_id))
            existing = cur.fetchone()
            
            if existing:
                # Update with new rating if provided
                if personal_rating is not None:
                    try:
                        query = "UPDATE user_collections SET personal_rating = ? WHERE user_id = ? AND game_id = ?"
                        if DB_TYPE == "postgres":
                            query = query.replace("?", "%s")
                        execute_query(ENGINE_CONN, query, (personal_rating, current_user["id"], game_id))
                        ENGINE_CONN.commit()
                        updated_count += 1
                    except Exception as e:
                        logger.warning(f"Error updating game {game_id} rating: {e}")
            else:
                # Add to collection with rating
                try:
                    query = "INSERT INTO user_collections (user_id, game_id, personal_rating) VALUES (?, ?, ?)"
                    if DB_TYPE == "postgres":
                        query = query.replace("?", "%s")
                    execute_query(ENGINE_CONN, query, (current_user["id"], game_id, personal_rating))
                    ENGINE_CONN.commit()
                    added_count += 1
                except Exception as e:
                    logger.warning(f"Error adding game {game_id} to collection: {e}")
                    skipped_count += 1
        
        ENGINE_CONN.commit()
        logger.info(f"Collection import complete: {added_count} added, {updated_count} updated, {skipped_count} skipped")
        
        return {
            "success": True,
            "added": added_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "total_fetched": len(games_data)
        }
    except Exception as e:
        logger.error(f"Error importing BGG collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to import collection: {str(e)}")


@app.get("/games/search")
def search_games(q: str, limit: int = 10):
    """Search games and features (mechanics, categories, designers, publishers) with lookahead. Cached for performance."""
    # Input validation and sanitization
    if not q:
        return {"games": [], "features": []}
    q = q.strip()
    if len(q) < 2:
        return {"games": [], "features": []}
    
    # Sanitize to prevent SQL injection (though parameterized queries are safe)
    q = q.replace("%", "").replace("_", "")[:100]  # Limit length
    
    # Check cache
    cache_key = f"game_search:{q}:{limit}"
    cached_result = get_cached(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        # Split query into words for better matching
        query_words = q.split()
        search_pattern = f"%{q}%"
        
        # Search for games
        if len(query_words) == 1:
            sql = """SELECT DISTINCT g.id, g.name, g.year_published, g.thumbnail, g.average_rating, g.num_ratings
                     FROM games g
                     LEFT JOIN game_mechanics gm ON gm.game_id = g.id
                     LEFT JOIN mechanics m ON m.id = gm.mechanic_id
                     LEFT JOIN game_categories gc ON gc.game_id = g.id
                     LEFT JOIN categories c ON c.id = gc.category_id
                     LEFT JOIN game_designers gd ON gd.game_id = g.id
                     LEFT JOIN designers d ON d.id = gd.designer_id
                     LEFT JOIN game_publishers gp ON gp.game_id = g.id
                     LEFT JOIN publishers p ON p.id = gp.publisher_id
                     WHERE LOWER(g.name) LIKE LOWER(?)
                        OR LOWER(m.name) LIKE LOWER(?)
                        OR LOWER(c.name) LIKE LOWER(?)
                        OR LOWER(d.name) LIKE LOWER(?)
                        OR LOWER(p.name) LIKE LOWER(?)
                     ORDER BY g.num_ratings DESC NULLS LAST, g.average_rating DESC NULLS LAST, g.name
                     LIMIT ?"""
            params = (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, limit)
        else:
            word_conditions = []
            for word in query_words:
                word_conditions.append(f"""(LOWER(g.name) LIKE LOWER(?) 
                    OR LOWER(m.name) LIKE LOWER(?) 
                    OR LOWER(c.name) LIKE LOWER(?) 
                    OR LOWER(d.name) LIKE LOWER(?)
                    OR LOWER(p.name) LIKE LOWER(?))""")
            
            conditions = " AND ".join(word_conditions)
            sql = f"""SELECT DISTINCT g.id, g.name, g.year_published, g.thumbnail, g.average_rating, g.num_ratings
                     FROM games g
                     LEFT JOIN game_mechanics gm ON gm.game_id = g.id
                     LEFT JOIN mechanics m ON m.id = gm.mechanic_id
                     LEFT JOIN game_categories gc ON gc.game_id = g.id
                     LEFT JOIN categories c ON c.id = gc.category_id
                     LEFT JOIN game_designers gd ON gd.game_id = g.id
                     LEFT JOIN designers d ON d.id = gd.designer_id
                     LEFT JOIN game_publishers gp ON gp.game_id = g.id
                     LEFT JOIN publishers p ON p.id = gp.publisher_id
                     WHERE {conditions}
                     ORDER BY g.num_ratings DESC NULLS LAST, g.average_rating DESC NULLS LAST, g.name
                     LIMIT ?"""
            params = tuple([f"%{word}%" for word in query_words for _ in range(5)] + [limit])
        
        cur = execute_query(ENGINE_CONN, sql, params)
        game_results = []
        seen_ids = set()
        for row in cur.fetchall():
            if row[0] not in seen_ids:
                game_id = row[0]
                # Get features for this game to show in search results (optimized - single query)
                features = []
                try:
                    # Single query to get all features at once for better performance
                    cur_f = execute_query(
                        ENGINE_CONN,
                        """SELECT 'mechanics' as type, m.name, '⚙️' as icon
                           FROM mechanics m JOIN game_mechanics gm ON gm.mechanic_id = m.id WHERE gm.game_id = ?
                           UNION ALL
                           SELECT 'categories' as type, c.name, '🏷️' as icon
                           FROM categories c JOIN game_categories gc ON gc.category_id = c.id WHERE gc.game_id = ?
                           UNION ALL
                           SELECT 'designers' as type, d.name, '👤' as icon
                           FROM designers d JOIN game_designers gd ON gd.designer_id = d.id WHERE gd.game_id = ?
                           UNION ALL
                           SELECT 'artists' as type, a.name, '🎨' as icon
                           FROM artists a JOIN game_artists ga ON ga.artist_id = a.id WHERE ga.game_id = ?
                           LIMIT 5""",
                        (game_id, game_id, game_id, game_id)
                    )
                    feature_rows = cur_f.fetchall() if cur_f else []
                    features = [(r[2], r[1]) for r in feature_rows if len(r) >= 3]
                except Exception as e:
                    logger.error(f"Error fetching features for game {game_id}: {e}")
                    pass
                
                game_results.append({
                    "id": game_id,
                    "name": row[1],
                    "year_published": row[2],
                    "thumbnail": row[3],
                    "average_rating": row[4],
                    "num_ratings": row[5],
                    "features": features[:5]  # Limit to 5 features for performance
                })
                seen_ids.add(game_id)
                if len(game_results) >= limit:
                    break
        
        # Search for features separately (mechanics, categories, designers, publishers)
        feature_results = []
        feature_limit = 10  # Limit features per type
        
        # Search mechanics
        try:
            cur_m = execute_query(
                ENGINE_CONN,
                """SELECT DISTINCT id, name FROM mechanics 
                   WHERE LOWER(name) LIKE LOWER(?) 
                   ORDER BY name LIMIT ?""",
                (search_pattern, feature_limit)
            )
            mechanics_rows = cur_m.fetchall()
            for row in mechanics_rows:
                if len(row) >= 2:
                    feature_results.append({
                        "type": "mechanics",
                        "id": row[0],
                        "name": row[1],
                        "icon": "⚙️"
                    })
        except Exception as e:
            logger.error(f"Error searching mechanics: {e}")
        
        # Search categories
        try:
            cur_c = execute_query(
                ENGINE_CONN,
                """SELECT DISTINCT id, name FROM categories 
                   WHERE LOWER(name) LIKE LOWER(?) 
                   ORDER BY name LIMIT ?""",
                (search_pattern, feature_limit)
            )
            categories_rows = cur_c.fetchall()
            for row in categories_rows:
                if len(row) >= 2:
                    feature_results.append({
                        "type": "categories",
                        "id": row[0],
                        "name": row[1],
                        "icon": "🏷️"
                    })
        except Exception as e:
            logger.error(f"Error searching categories: {e}")
        
        # Search designers
        try:
            cur_d = execute_query(
                ENGINE_CONN,
                """SELECT DISTINCT id, name FROM designers 
                   WHERE LOWER(name) LIKE LOWER(?) 
                   ORDER BY name LIMIT ?""",
                (search_pattern, feature_limit)
            )
            designers_rows = cur_d.fetchall()
            for row in designers_rows:
                if len(row) >= 2:
                    feature_results.append({
                        "type": "designers",
                        "id": row[0],
                        "name": row[1],
                        "icon": "👤"
                    })
        except Exception as e:
            logger.error(f"Error searching designers: {e}")
        
        # Search artists
        try:
            cur_a = execute_query(
                ENGINE_CONN,
                """SELECT DISTINCT id, name FROM artists 
                   WHERE LOWER(name) LIKE LOWER(?) 
                   ORDER BY name LIMIT ?""",
                (search_pattern, feature_limit)
            )
            artists_rows = cur_a.fetchall()
            for row in artists_rows:
                if len(row) >= 2:
                    feature_results.append({
                        "type": "artists",
                        "id": row[0],
                        "name": row[1],
                        "icon": "🎨"
                    })
        except Exception as e:
            logger.error(f"Error searching artists: {e}")
        
        # Search publishers
        try:
            cur_p = execute_query(
                ENGINE_CONN,
                """SELECT DISTINCT id, name FROM publishers 
                   WHERE LOWER(name) LIKE LOWER(?) 
                   ORDER BY name LIMIT ?""",
                (search_pattern, feature_limit)
            )
            publishers_rows = cur_p.fetchall()
            for row in publishers_rows:
                if len(row) >= 2:
                    feature_results.append({
                        "type": "publishers",
                        "id": row[0],
                        "name": row[1],
                        "icon": "🏢"
                    })
        except Exception as e:
            logger.error(f"Error searching publishers: {e}")
        
        result = {
            "games": game_results,
            "features": feature_results
        }
        
        
        # Cache results
        set_cached(cache_key, result)
        logger.debug(f"Search: '{q}' returned {len(game_results)} games and {len(feature_results)} features")
        return result
    except Exception as e:
        logger.error(f"Database error in search: {e}", exc_info=True)
        return {"games": [], "features": []}


@app.get("/profile/collection")
def get_collection(
    sort_by: str = "year_published",
    order: str = "desc",
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get user's game collection with sorting options."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    # Validate sort_by and order
    valid_sort_fields = ["added_at", "name", "year_published", "rank", "average_rating"]
    if sort_by not in valid_sort_fields:
        sort_by = "year_published"
    if order.lower() not in ["asc", "desc"]:
        order = "desc"
    
    # Build ORDER BY clause
    order_by = f"{sort_by} {order.upper()}"
    if sort_by == "added_at":
        order_by = f"uc.added_at {order.upper()}"
    elif sort_by == "name":
        order_by = f"g.name {order.upper()}"
    elif sort_by == "year_published":
        order_by = f"g.year_published {order.upper()}"
    elif sort_by == "average_rating":
        order_by = f"g.average_rating {order.upper()}"
    
    # Check if personal_rating column exists, if not use NULL (SQLite only)
    has_personal_rating = True  # Assume it exists in PostgreSQL
    if DB_TYPE == "sqlite":
        try:
            cur = execute_query(ENGINE_CONN, "PRAGMA table_info(user_collections)")
            columns = [row[1] for row in cur.fetchall()]
            has_personal_rating = "personal_rating" in columns
        except:
            has_personal_rating = False
    
    personal_rating_col = "uc.personal_rating" if has_personal_rating else "NULL as personal_rating"
    
    query = f"""SELECT uc.game_id, g.name, g.year_published, g.thumbnail, uc.added_at,
                g.average_rating, {personal_rating_col}
           FROM user_collections uc
           JOIN games g ON uc.game_id = g.id
           WHERE uc.user_id = ?
           ORDER BY {order_by}"""
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    cur = execute_query(ENGINE_CONN, query, (current_user["id"],))
    collection = []
    for row in cur.fetchall():
        collection.append({
            "game_id": row[0],
            "name": row[1],
            "year_published": row[2],
            "thumbnail": row[3],
            "added_at": row[4],
            "average_rating": row[5],
            "personal_rating": row[6]
        })
    return collection


class AddToCollectionRequest(BaseModel):
    game_id: int


@app.post("/profile/collection")
def add_to_collection(req: AddToCollectionRequest, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Add a game to user's collection."""
    game_id = req.game_id
    # Verify game exists
    cur = execute_query(ENGINE_CONN, "SELECT id FROM games WHERE id = ?", (game_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Add to collection (ignore if already exists)
    if DB_TYPE == "postgres":
        insert_sql = "INSERT INTO user_collections (user_id, game_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"
    else:
        insert_sql = "INSERT OR IGNORE INTO user_collections (user_id, game_id) VALUES (?, ?)"
    execute_query(ENGINE_CONN, insert_sql, (current_user["id"], game_id))
    ENGINE_CONN.commit()
    logger.info(f"Added game {game_id} to collection for user {current_user['id']}")
    return {"success": True, "game_id": game_id}


@app.delete("/profile/collection/{game_id}")
def remove_from_collection(game_id: int, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Remove a game from user's collection."""
    query = "DELETE FROM user_collections WHERE user_id = ? AND game_id = ?"
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    cur = execute_query(ENGINE_CONN, query, (current_user["id"], game_id))
    ENGINE_CONN.commit()
    rowcount = cur.rowcount if hasattr(cur, 'rowcount') else (0 if not cur.fetchone() else 1)
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Game not in collection")
    return {"success": True}


@app.get("/chat/history")
def get_chat_history(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get list of chat threads for the user."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    cur = execute_query(
        ENGINE_CONN,
        """SELECT id, title, created_at, updated_at
           FROM chat_threads
           WHERE user_id = ?
           ORDER BY updated_at DESC""",
        (current_user["id"],)
    )
    threads = []
    for row in cur.fetchall():
        threads.append({
            "id": row[0],
            "title": row[1] or f"Chat {row[0]}",
            "created_at": row[2],
            "updated_at": row[3]
        })
    return threads


@app.get("/chat/history/{thread_id}")
def get_chat_thread(thread_id: int, current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get messages for a specific chat thread."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    # Verify thread belongs to user
    query = "SELECT id FROM chat_threads WHERE id = ? AND user_id = ?"
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    cur = execute_query(ENGINE_CONN, query, (thread_id, current_user["id"]))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Get messages
    query = "SELECT id, role, message, metadata, created_at FROM chat_messages WHERE thread_id = ? ORDER BY created_at ASC"
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    cur = execute_query(ENGINE_CONN, query, (thread_id,))
    messages = []
    for row in cur.fetchall():
        messages.append({
            "id": row[0],
            "role": row[1],
            "message": row[2],
            "metadata": json.loads(row[3]) if row[3] else None,
            "created_at": row[4]
        })
    return messages


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> ChatResponse:
    """Chat endpoint with history saving. Works with or without authentication."""
    assert ENGINE is not None, "ENGINE not initialized"
    logger.info(f"Chat request from user: {current_user['id'] if current_user else 'anonymous'}")

    # Handle authenticated vs anonymous users
    if current_user:
        user_id = str(current_user["id"])
        user_collection = load_user_collection(user_id)
    else:
        user_id = "anonymous"
        user_collection = set()
        logger.debug("Anonymous user chat request")

    # Input validation and sanitization
    message = req.message.strip()[:1000]  # Limit message length
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    context = req.context or {}
    context["user_collection_ids"] = list(user_collection)
    
    # If game was selected from search, bypass NLU game resolution
    if req.selected_game_id:
        logger.debug(f"Using selected game_id {req.selected_game_id}, bypassing NLU")
        context["selected_game_id"] = req.selected_game_id
    
    query_spec = interpret_message(user_id, message, context)
    
    # Override base_game_id if game was selected from search
    if req.selected_game_id:
        query_spec["base_game_id"] = req.selected_game_id
        logger.debug(f"Overriding base_game_id to {req.selected_game_id}")

    intent = query_spec.get("intent", "recommend_similar")
    reply_text = "I'm not sure what to do with that yet."
    results: Optional[List[Dict[str, Any]]] = None
    
    # Initialize thread_id from request (will be updated if new thread is created)
    thread_id = req.thread_id

    if intent == "collection_recommendation":
        # "Do I need X in my collection?" feature
        base_game_id = query_spec.get("base_game_id")
        if not base_game_id or not current_user:
            reply_text = "I need to know which game you're asking about, and you need to be logged in to check your collection."
            results = []
        else:
            try:
                base_game_id = int(base_game_id)
                # Get user's collection
                user_collection = load_user_collection(str(current_user["id"]))
                
                # Check if game is already in collection
                if base_game_id in user_collection:
                    reply_text = f"This game is already in your collection!"
                    results = []
                else:
                    # Get game features
                    from backend.reasoning_utils import get_game_features, get_feature_rarity_weights
                    game_features = get_game_features(ENGINE_CONN, base_game_id)
                    
                    # Find top 5 similar games in collection
                    similar_games = []  # List of (game_id, similarity, overlaps, collection_features)
                    
                    for collection_game_id in user_collection:
                        try:
                            collection_features = get_game_features(ENGINE_CONN, collection_game_id)
                            from backend.reasoning_utils import compute_meta_similarity
                            similarity, overlaps, _ = compute_meta_similarity(game_features, collection_features)
                            similar_games.append((collection_game_id, similarity, overlaps, collection_features))
                        except Exception as e:
                            logger.debug(f"Error comparing with game {collection_game_id}: {e}")
                            continue
                    
                    # Sort by similarity and take top 5
                    similar_games.sort(key=lambda x: x[1], reverse=True)
                    top_similar_games = similar_games[:5]
                    
                    if not top_similar_games:
                        reply_text = "I couldn't find any similar games in your collection to compare with."
                        results = []
                    else:
                        max_similarity = top_similar_games[0][1]
                        most_similar_game_id = top_similar_games[0][0]
                        most_similar_features = top_similar_games[0][2]
                        
                        # Get rarity weights for missing features (need to call for each feature type)
                        rarity_weights = {}
                        for feature_type in ["mechanics", "categories", "designers", "families"]:
                            rarity_weights[feature_type] = get_feature_rarity_weights(ENGINE_CONN, feature_type)
                        
                        # Find features in target game that are NOT present in ANY game in the collection
                        # Build a set of all features present in any collection game
                        all_collection_features = {
                            "mechanics": set(),
                            "categories": set(),
                            "designers": set(),
                            "families": set()
                        }
                        
                        for collection_game_id in user_collection:
                            try:
                                collection_features = get_game_features(ENGINE_CONN, collection_game_id)
                                for feature_type in ["mechanics", "categories", "designers", "families"]:
                                    all_collection_features[feature_type].update(collection_features.get(feature_type, set()))
                            except Exception as e:
                                logger.debug(f"Error getting features for collection game {collection_game_id}: {e}")
                                continue
                        
                        # Find features unique to target game (not in any collection game)
                        unique_features = {}
                        for feature_type in ["mechanics", "categories", "designers", "families"]:
                            target_features = game_features.get(feature_type, set())
                            collection_features_set = all_collection_features[feature_type]
                            unique = target_features - collection_features_set
                            if unique:
                                unique_features[feature_type] = list(unique)
                        
                        # Calculate average rarity of unique features (features not in any collection game)
                        avg_rarity = 1.0  # Default (common)
                        if unique_features:
                            rarities = []
                            for feature_type, features in unique_features.items():
                                if feature_type in rarity_weights:
                                    for feature in features:
                                        rarity = rarity_weights[feature_type].get(feature, 1.0)
                                        rarities.append(rarity)
                            if rarities:
                                avg_rarity = sum(rarities) / len(rarities)
                        
                        # Decision logic:
                        # - If similarity > 0.65 and unique features are not rare (avg_rarity > 0.5) → "No"
                        # - Otherwise → "Yes"
                        too_similar = max_similarity > 0.65
                        features_not_rare = avg_rarity > 0.5
                        
                        # Build results with top 5 similar games
                        results = []
                        for collection_game_id, similarity, overlaps, collection_features in top_similar_games:
                            try:
                                # Fetch game details
                                cur = execute_query(
                                    ENGINE_CONN,
                                    "SELECT id, name, year_published, thumbnail, average_rating, num_ratings, min_players, max_players, description FROM games WHERE id = ?",
                                    (collection_game_id,)
                                )
                                row = cur.fetchone()
                                if not row:
                                    continue
                                
                                # Get designers
                                designers = []
                                try:
                                    cur_d = execute_query(
                                        ENGINE_CONN,
                                        """SELECT d.name FROM designers d
                                           JOIN game_designers gd ON gd.designer_id = d.id
                                           WHERE gd.game_id = ? ORDER BY d.name""",
                                        (collection_game_id,)
                                    )
                                    designers = [r[0] for r in cur_d.fetchall()]
                                except:
                                    pass
                                
                                # Calculate similarities (shared features)
                                shared_mechanics = sorted(overlaps.get("shared_mechanics", []))
                                shared_categories = sorted(overlaps.get("shared_categories", []))
                                shared_designers = sorted(overlaps.get("shared_designers", []))
                                shared_families = sorted(overlaps.get("shared_families", []))
                                
                                # Calculate differences
                                # Missing: features in target game but not in collection game
                                missing_mechanics = sorted(game_features.get("mechanics", set()) - collection_features.get("mechanics", set()))
                                missing_categories = sorted(game_features.get("categories", set()) - collection_features.get("categories", set()))
                                missing_designers = sorted(game_features.get("designers", set()) - collection_features.get("designers", set()))
                                missing_families = sorted(game_features.get("families", set()) - collection_features.get("families", set()))
                                
                                # Extra: features in collection game but not in target game
                                extra_mechanics = sorted(collection_features.get("mechanics", set()) - game_features.get("mechanics", set()))
                                extra_categories = sorted(collection_features.get("categories", set()) - game_features.get("categories", set()))
                                extra_designers = sorted(collection_features.get("designers", set()) - game_features.get("designers", set()))
                                extra_families = sorted(collection_features.get("families", set()) - game_features.get("families", set()))
                                
                                results.append({
                                    "game_id": collection_game_id,
                                    "name": row[1],
                                    "year_published": row[2],
                                    "thumbnail": row[3],
                                    "average_rating": row[4],
                                    "num_ratings": row[5],
                                    "min_players": row[6],
                                    "max_players": row[7],
                                    "description": row[8] if len(row) > 8 and row[8] else None,
                                    "designers": designers,
                                    "similarity_score": similarity,
                                    "final_score": similarity,  # For consistency with other results
                                    "embedding_similarity": similarity,  # For consistency
                                    # Shared features (similarities)
                                    "shared_mechanics": shared_mechanics,
                                    "shared_categories": shared_categories,
                                    "shared_designers": shared_designers,
                                    "shared_families": shared_families,
                                    # Missing features (what target game has that collection game doesn't)
                                    "missing_mechanics": missing_mechanics,
                                    "missing_categories": missing_categories,
                                    "missing_designers": missing_designers,
                                    "missing_families": missing_families,
                                    # Extra features (what collection game has that target game doesn't)
                                    "extra_mechanics": extra_mechanics,
                                    "extra_categories": extra_categories,
                                    "extra_designers": extra_designers,
                                    "extra_families": extra_families,
                                })
                            except Exception as e:
                                logger.warning(f"Error building result for game {collection_game_id}: {e}")
                                continue
                        
                        if too_similar and features_not_rare:
                            # Get name of most similar game
                            similar_game_name = results[0]["name"] if results else "a game in your collection"
                            reply_text = f"No, you probably don't need this game. It's very similar to '{similar_game_name}' in your collection (similarity: {max_similarity:.1%}), and the unique features it offers are fairly common."
                        else:
                            reasons = []
                            if not too_similar:
                                reasons.append("it's quite different from games in your collection")
                            if not features_not_rare:
                                reasons.append("it offers rare/unique features")
                            
                            reason_text = " and ".join(reasons) if reasons else "it would add value to your collection"
                            reply_text = f"Yes, this game could be a good addition! {reason_text.capitalize()}."
                
            except Exception as e:
                logger.error(f"Error in collection recommendation: {e}", exc_info=True)
                reply_text = "I encountered an error while analyzing your collection. Please try again."
                results = []
        
        return ChatResponse(
            reply_text=reply_text,
            results=results,
            query_spec=query_spec,
            thread_id=thread_id if current_user else None,
            ab_responses=None
        )

    if intent == "recommend_similar":
        base_game_id = query_spec.get("base_game_id")
        include_features = query_spec.get("include_features")
        required_feature_values = query_spec.get("required_feature_values")
        
        # Allow search without game_id if features are specified
        if base_game_id is None:
            # Check if we have features to search by
            has_features = (include_features and len(include_features) > 0) or (required_feature_values and len(required_feature_values) > 0)
            if not has_features:
                logger.warning("base_game_id is None and no features specified")
                reply_text = "I couldn't identify which game you're asking about. Please specify a game name or features."
                results = []
                return ChatResponse(
                    reply_text=reply_text,
                    results=results,
                    query_spec=query_spec,
                    thread_id=thread_id if current_user else None,
                    ab_responses=None
                )
            else:
                # Search by features only - we'll handle this differently
                logger.info("Searching by features only (no base game)")
                base_game_id = None  # Will trigger feature-only search
        else:
            try:
                base_game_id = int(base_game_id)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid base_game_id: {base_game_id}, error: {e}")
                reply_text = f"I couldn't identify which game you're asking about. Please specify a game name."
                results = []
                base_game_id = None
        
        constraints = query_spec.get("constraints") or {}
        original_scope = query_spec.get("scope", "global")  # Track original scope before it might change
        scope = original_scope
        top_k = int(query_spec.get("top_k", 5))

        allowed_ids: Optional[Set[int]] = None
        if scope == "user_collection":
            allowed_ids = user_collection or None
            if not allowed_ids or len(allowed_ids) == 0:
                scope = "global"
                logger.debug("User collection is empty, falling back to global scope")
            else:
                logger.debug(f"Searching in collection with {len(allowed_ids)} games")

        # Extract include/exclude features from query_spec (set by NLU)
        include_features = query_spec.get("include_features")
        exclude_features = query_spec.get("exclude_features")
        
        # Check for A/B test configs
        ab_test_configs = {}
        try:
            query = "SELECT config_key, config_value FROM ab_test_configs WHERE is_active = ?"
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
                cur = execute_query(ENGINE_CONN, query, (True,))
            else:
                cur = execute_query(ENGINE_CONN, query, (1,))
            for row in cur.fetchall():
                try:
                    ab_test_configs[row[0]] = json.loads(row[1])
                except:
                    ab_test_configs[row[0]] = row[1]
        except Exception as e:
            logger.debug(f"Error loading A/B test configs: {e}")
        
        # Check if rarity weighting is enabled (via A/B test or direct config)
        use_rarity_weighting = ab_test_configs.get("use_rarity_weighting", {}).get("enabled", False)
        # Also check if there's a direct config request
        use_rarity_weighting = query_spec.get("use_rarity_weighting", use_rarity_weighting)
        
        # Get excluded feature values from query_spec (set by user removing chips)
        excluded_feature_values = query_spec.get("excluded_feature_values")
        if excluded_feature_values:
            # Convert to proper format: {"mechanics": {"Deck Building"}, "categories": {"Fantasy"}}
            excluded_feature_values = {
                k: set(v) if isinstance(v, list) else {v} if v else set()
                for k, v in excluded_feature_values.items()
            }
        
        # Get required feature values from query_spec (set by user clicking chips to require features)
        required_feature_values = query_spec.get("required_feature_values")
        if required_feature_values:
            # Convert to proper format: {"mechanics": {"Deck Building"}, "categories": {"Fantasy"}}
            required_feature_values = {
                k: set(v) if isinstance(v, list) else {v} if v else set()
                for k, v in required_feature_values.items()
            }
            logger.info(f"Required feature values: {required_feature_values}")
        else:
            required_feature_values = None
        
        logger.info(f"Search params: base_game_id={base_game_id}, include_features={include_features}, exclude_features={exclude_features}, constraints={constraints}, use_rarity_weighting={use_rarity_weighting}, excluded_feature_values={excluded_feature_values}, required_feature_values={required_feature_values}")
        
        try:
            if base_game_id is None:
                # Feature-only search - find games with required features, ordered by rating
                results = search_by_features_only(
                    required_feature_values=required_feature_values,
                    include_features=include_features,
                    exclude_features=exclude_features,
                    constraints=constraints,
                    allowed_ids=allowed_ids,
                    top_k=top_k
                )
            else:
                # Normal similarity search with base game
                results = ENGINE.search_similar(
                    game_id=base_game_id,
                    top_k=top_k,
                    include_self=False,
                    constraints=constraints,
                    allowed_ids=allowed_ids,
                    explain=True,
                    include_features=include_features,
                    exclude_features=exclude_features,
                    use_rarity_weighting=use_rarity_weighting,
                    excluded_feature_values=excluded_feature_values,
                    required_feature_values=required_feature_values,
                )
            logger.debug(f"Found {len(results)} results for game_id={base_game_id}, scope={scope}")
            
            # If no results found, try with loosened constraints and features
            if not results:
                logger.debug("No results found, attempting with loosened constraints/features")
                
                # First try: if searching in collection and no results, try global scope
                if allowed_ids and len(allowed_ids) > 0:
                    logger.debug(f"No results in collection ({len(allowed_ids)} games), trying global scope")
                    try:
                        results = ENGINE.search_similar(
                            game_id=base_game_id,
                            top_k=top_k * 2,
                            include_self=False,
                            constraints=constraints,
                            allowed_ids=None,  # Remove collection restriction - search globally
                            explain=True,
                            include_features=include_features,
                            exclude_features=exclude_features,
                            use_rarity_weighting=use_rarity_weighting,
                            excluded_feature_values=excluded_feature_values,
                            required_feature_values=required_feature_values,  # Keep required features!
                        )
                        results = results[:top_k] if results else []
                        logger.debug(f"Found {len(results)} results in global scope")
                    except Exception as search_err:
                        logger.error(f"Error in global scope search: {search_err}", exc_info=True)
                
                # If still no results, try without constraints and features
                if not results:
                    logger.debug(f"Retrying without constraints and features")
                    try:
                        results = ENGINE.search_similar(
                            game_id=base_game_id,
                            top_k=top_k * 2,
                            include_self=False,
                            constraints=None,  # Remove ALL constraints
                            allowed_ids=None,  # Remove collection restriction
                            explain=True,
                            include_features=None,
                            exclude_features=None,
                            use_rarity_weighting=use_rarity_weighting,
                            excluded_feature_values=excluded_feature_values,
                        )
                        results = results[:top_k] if results else []
                        logger.debug(f"Found {len(results)} results without constraints/features")
                    except Exception as search_err:
                        logger.error(f"Error in unconstrained search: {search_err}", exc_info=True)
                
                # If still no results, try embedding-only (no explain mode)
                if not results:
                    logger.debug(f"Retrying with embedding-only (no explain, no constraints, no features, but keeping required features)")
                    try:
                        results = ENGINE.search_similar(
                            game_id=base_game_id,
                            top_k=top_k,
                            include_self=False,
                            constraints=None,
                            allowed_ids=None,  # Remove collection restriction
                            explain=False,  # Use embedding-only (no feature filtering)
                            include_features=None,
                            exclude_features=None,
                            required_feature_values=required_feature_values,  # Keep required features!
                        )
                        logger.debug(f"Found {len(results)} results with embedding-only search")
                    except Exception as search_err:
                        logger.error(f"Error in embedding-only search: {search_err}", exc_info=True)
        except Exception as e:
            logger.error(f"Error searching similar games: {e}", exc_info=True)
            results = []

        # Track if scope was changed from user_collection to global
        scope_changed = False
        if original_scope == "user_collection" and scope == "global" and results:
            scope_changed = True
        
        if results:
            excluded_text = ""
            if exclude_features:
                excluded_text = f" (excluding: {', '.join(exclude_features)})"
            
            scope_notice = ""
            if scope_changed:
                scope_notice = " No similar games found in your collection, so I'm showing results from the global database."
            
            reply_text = (
                f"Here are some games that feel close to your base game "
                f"(intent: {intent}, scope: {scope}){excluded_text}.{scope_notice}"
            )
        else:
            excluded_text = ""
            if exclude_features:
                excluded_text = f" Excluded features: {', '.join(exclude_features)}."
            reply_text = f"I couldn't find any games matching those filters.{excluded_text}"

    elif intent == "compare_pair":
        a = query_spec.get("game_a_id")
        b = query_spec.get("game_b_id")
        if not a or not b:
            reply_text = "I need two games to compare. Please specify both games."
            results = []
        else:
            # Get game names for display
            query = "SELECT name FROM games WHERE id IN (?, ?)"
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
            cur = execute_query(ENGINE_CONN, query, (a, b))
            game_names = {row[0]: row[0] for row in cur.fetchall()}
            query = "SELECT id, name FROM games WHERE id IN (?, ?)"
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
            cur = execute_query(ENGINE_CONN, query, (a, b))
            game_info = {row[0]: row[1] for row in cur.fetchall()}
            game_a_name = game_info.get(a, f"Game {a}")
            game_b_name = game_info.get(b, f"Game {b}")
            
            # compare_two_games implementation as before
            cmp_result = compare_two_games(ENGINE, a, b)
            # Format result for frontend (add game names and ensure all fields exist)
            result_dict = {
                "game_id": a,  # Use first game as primary
                "name": f"{game_a_name} vs {game_b_name}",
                "game_a_id": a,
                "game_b_id": b,
                "meta_score": cmp_result.get("meta_score", 0.0),
                "final_score": cmp_result.get("meta_score", 0.0),
                "embedding_similarity": cmp_result.get("meta_score", 0.0),  # Use meta_score as similarity
                "reason_summary": cmp_result.get("reason_summary", "Comparison completed"),
                "overlaps": cmp_result.get("overlaps", {}),
            }
            results = [result_dict]
            reply_text = (
                f"Here's how {game_a_name} and {game_b_name} relate based on mechanics, theme and metadata.\n"
                f"Similarity score: {cmp_result.get('meta_score', 0.0):.2f}\n"
                f"{cmp_result.get('reason_summary', 'Comparison completed')}"
            )

    # Check for A/B testing (only for recommend_similar with results and base_game_id)
    ab_responses = None
    if intent == "recommend_similar" and results and base_game_id is not None:
        # Check if any A/B test configs are active
        ab_configs_to_test = []
        for config_key, config_data in ab_test_configs.items():
            if isinstance(config_data, dict) and config_data.get("enabled", False):
                ab_configs_to_test.append((config_key, config_data))
        
        if ab_configs_to_test and base_game_id is not None:
            # Check user's A/B test preferences
            user_ab_preferences = {}
            if current_user:
                try:
                    query = "SELECT config_key, preferred_value FROM user_ab_preferences WHERE user_id = ?"
                    if DB_TYPE == "postgres":
                        query = query.replace("?", "%s")
                    cur_prefs = execute_query(ENGINE_CONN, query, (int(current_user["id"]),))
                    for row in cur_prefs.fetchall():
                        user_ab_preferences[row[0]] = row[1]
                except Exception as e:
                    logger.debug(f"Error loading user A/B preferences: {e}")
            
            # Generate A/B responses for each active config (only if we have a base game)
            ab_responses = []
            for config_key, config_data in ab_configs_to_test:
                # Check if user has a preference for this config
                user_preference = user_ab_preferences.get(config_key)
                if user_preference:
                    # User has a preference - only show that variant
                    logger.info(f"User has preference for {config_key}: {user_preference}, showing only that variant")
                    # Determine which config value to use based on preference
                    if config_key == "use_rarity_weighting" or "rarity" in config_key.lower():
                        use_rarity = (user_preference == "B")
                    else:
                        use_rarity = use_rarity_weighting
                    
                    # Generate only the preferred variant
                    preferred_results = ENGINE.search_similar(
                        game_id=base_game_id,
                        top_k=top_k,
                        include_self=False,
                        constraints=constraints,
                        allowed_ids=allowed_ids,
                        explain=True,
                        include_features=include_features,
                        exclude_features=exclude_features,
                        use_rarity_weighting=use_rarity,
                        excluded_feature_values=excluded_feature_values,
                        required_feature_values=required_feature_values,
                    )
                    
                    # Return as regular results (not A/B test)
                    results = preferred_results
                    ab_responses = None  # Don't show A/B test question
                    continue  # Skip A/B test generation for this config
                # Determine the config value for A and B based on the config_key
                # Check if this config is related to rarity weighting (flexible matching)
                if config_key == "use_rarity_weighting" or "rarity" in config_key.lower():
                    # For rarity weighting, A = False, B = True
                    use_rarity_a = False
                    use_rarity_b = True
                else:
                    # For other configs, use the current value for both (not testing this config)
                    use_rarity_a = use_rarity_weighting
                    use_rarity_b = use_rarity_weighting
                
                logger.info(f"A/B test for {config_key}: A uses rarity_weighting={use_rarity_a}, B uses rarity_weighting={use_rarity_b}")
                
                # Generate response A (config = False)
                results_a = ENGINE.search_similar(
                    game_id=base_game_id,
                    top_k=top_k,
                    include_self=False,
                    constraints=constraints,
                    allowed_ids=allowed_ids,
                    explain=True,
                    include_features=include_features,
                    exclude_features=exclude_features,
                    use_rarity_weighting=use_rarity_a,
                    excluded_feature_values=excluded_feature_values,
                    required_feature_values=required_feature_values,
                )
                
                # Generate response B (config = True)
                results_b = ENGINE.search_similar(
                    game_id=base_game_id,
                    top_k=top_k,
                    include_self=False,
                    constraints=constraints,
                    allowed_ids=allowed_ids,
                    explain=True,
                    include_features=include_features,
                    exclude_features=exclude_features,
                    use_rarity_weighting=use_rarity_b,
                    excluded_feature_values=excluded_feature_values,
                    required_feature_values=required_feature_values,
                )
                
                logger.info(f"A/B test results: A has {len(results_a)} results, B has {len(results_b)} results")
                
                # Create A/B test question if it doesn't exist
                ab_question = _get_or_create_ab_question(ENGINE_CONN, config_key, config_data)
                
                ab_responses.append({
                    "config_key": config_key,
                    "config_name": config_data.get("name", config_key),
                    "response_a": {
                        "results": results_a,
                        "config_value": False,
                        "label": config_data.get("label_a", "Option A")
                    },
                    "response_b": {
                        "results": results_b,
                        "config_value": True,
                        "label": config_data.get("label_b", "Option B")
                    },
                    "question_id": ab_question["id"],
                    "question_text": ab_question["question_text"],
                    "options": ab_question["options"]
                })

    # Save to chat history (only if authenticated)
    if current_user:
        if not thread_id:
            # Create new thread
            insert_sql = "INSERT INTO chat_threads (user_id, title) VALUES (?, ?)"
            if DB_TYPE == "postgres":
                insert_sql = insert_sql.replace("?", "%s") + " RETURNING id"
            
            try:
                cur = execute_query(
                    ENGINE_CONN,
                    insert_sql,
                    (current_user["id"], req.message[:50])  # Use first 50 chars as title
                )
                ENGINE_CONN.commit()
                if DB_TYPE == "postgres":
                    thread_id = cur.fetchone()[0]
                else:
                    thread_id = cur.lastrowid
                logger.debug(f"Created new chat thread {thread_id} for user {current_user['id']}")
            except Exception as e:
                # Handle sequence sync issues for PostgreSQL
                is_unique_violation = False
                if DB_TYPE == "postgres":
                    if psycopg2 and psycopg2.errors:
                        is_unique_violation = isinstance(e, psycopg2.errors.UniqueViolation)
                    else:
                        # Fallback check if psycopg2.errors not available
                        is_unique_violation = "UniqueViolation" in str(type(e).__name__) or "duplicate key" in str(e).lower()
                
                if is_unique_violation:
                    logger.warning(f"Sequence out of sync for chat_threads, fixing: {e}")
                    try:
                        # Fix the sequence by setting it to max(id) + 1
                        fix_seq_query = "SELECT setval('chat_threads_id_seq', COALESCE((SELECT MAX(id) FROM chat_threads), 0) + 1, false)"
                        execute_query(ENGINE_CONN, fix_seq_query)
                        ENGINE_CONN.commit()
                        # Retry the insert
                        cur = execute_query(
                            ENGINE_CONN,
                            insert_sql,
                            (current_user["id"], req.message[:50])
                        )
                        ENGINE_CONN.commit()
                        thread_id = cur.fetchone()[0]
                        logger.info(f"Fixed sequence and created new chat thread {thread_id} for user {current_user['id']}")
                    except Exception as retry_error:
                        logger.error(f"Failed to fix sequence and retry insert: {retry_error}", exc_info=True)
                        raise
                else:
                    raise
        
        # Save user message
        user_msg_sql = "INSERT INTO chat_messages (thread_id, role, message) VALUES (?, ?, ?)"
        if DB_TYPE == "postgres":
            user_msg_sql = user_msg_sql.replace("?", "%s")
        try:
            execute_query(
                ENGINE_CONN,
                user_msg_sql,
                (thread_id, "user", req.message)
            )
        except Exception as e:
            # Handle sequence sync issues for PostgreSQL
            is_unique_violation = False
            if DB_TYPE == "postgres":
                if psycopg2 and psycopg2.errors:
                    is_unique_violation = isinstance(e, psycopg2.errors.UniqueViolation)
                else:
                    is_unique_violation = "UniqueViolation" in str(type(e).__name__) or "duplicate key" in str(e).lower()
            
            if is_unique_violation:
                logger.warning(f"Sequence out of sync for chat_messages, fixing: {e}")
                try:
                    # Fix the sequence by setting it to max(id) + 1
                    fix_seq_query = "SELECT setval('chat_messages_id_seq', COALESCE((SELECT MAX(id) FROM chat_messages), 0) + 1, false)"
                    execute_query(ENGINE_CONN, fix_seq_query)
                    ENGINE_CONN.commit()
                    # Retry the insert
                    execute_query(
                        ENGINE_CONN,
                        user_msg_sql,
                        (thread_id, "user", req.message)
                    )
                    logger.info(f"Fixed sequence and inserted user message for thread {thread_id}")
                except Exception as retry_error:
                    logger.error(f"Failed to fix sequence and retry user message insert: {retry_error}", exc_info=True)
                    raise
            else:
                raise
        
        # Save assistant message
        metadata = {
            "results": results,
            "query_spec": query_spec
        }
        assistant_msg_sql = "INSERT INTO chat_messages (thread_id, role, message, metadata) VALUES (?, ?, ?, ?)"
        if DB_TYPE == "postgres":
            assistant_msg_sql = assistant_msg_sql.replace("?", "%s")
        try:
            execute_query(
                ENGINE_CONN,
                assistant_msg_sql,
                (thread_id, "assistant", reply_text, json.dumps(metadata))
            )
        except Exception as e:
            # Handle sequence sync issues for PostgreSQL
            is_unique_violation = False
            if DB_TYPE == "postgres":
                if psycopg2 and psycopg2.errors:
                    is_unique_violation = isinstance(e, psycopg2.errors.UniqueViolation)
                else:
                    is_unique_violation = "UniqueViolation" in str(type(e).__name__) or "duplicate key" in str(e).lower()
            
            if is_unique_violation:
                logger.warning(f"Sequence out of sync for chat_messages, fixing: {e}")
                try:
                    # Fix the sequence by setting it to max(id) + 1
                    fix_seq_query = "SELECT setval('chat_messages_id_seq', COALESCE((SELECT MAX(id) FROM chat_messages), 0) + 1, false)"
                    execute_query(ENGINE_CONN, fix_seq_query)
                    ENGINE_CONN.commit()
                    # Retry the insert
                    execute_query(
                        ENGINE_CONN,
                        assistant_msg_sql,
                        (thread_id, "assistant", reply_text, json.dumps(metadata))
                    )
                    logger.info(f"Fixed sequence and inserted assistant message for thread {thread_id}")
                except Exception as retry_error:
                    logger.error(f"Failed to fix sequence and retry assistant message insert: {retry_error}", exc_info=True)
                    raise
            else:
                raise
        
        # Update thread updated_at
        execute_query(
            ENGINE_CONN,
            "UPDATE chat_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (thread_id,)
        )
        ENGINE_CONN.commit()
        logger.debug(f"Saved messages to thread {thread_id}")
    else:
        logger.debug("Skipping history save for anonymous user")

    return ChatResponse(
        reply_text=reply_text,
        results=results,
        query_spec=query_spec,
        thread_id=thread_id if current_user else None,
        ab_responses=ab_responses
    )


class ImageGenerateRequest(BaseModel):
    game_id: Optional[int] = None
    context: Optional[str] = None
    api_type: Optional[str] = "stable_diffusion"

@app.post("/image/generate")
async def generate_from_image(
    req: ImageGenerateRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Fake-door: Store image upload interaction for later analysis."""
    user_id = current_user["id"] if current_user else None
    logger.info(f"Image upload fake-door request from user: {user_id or 'anonymous'}")
    
    # Get game_id and context from request body (JSON)
    game_id = req.game_id
    context = req.context
    api_type = req.api_type or "stable_diffusion"
    
    # Require game_id for fake-door
    if not game_id:
        raise HTTPException(status_code=400, detail="game_id is required")
    
    try:
        # Get game name for context
        game_name = None
        try:
            cur = execute_query(ENGINE_CONN, "SELECT name FROM games WHERE id = ?", (game_id,))
            row = cur.fetchone()
            if row:
                game_name = row[0]
        except:
            pass
        
        # Store interaction data
        interaction_context = {
            "game_id": game_id,
            "game_name": game_name,
            "context": context,
            "api_type": api_type
        }
        
        metadata = {
            "game_id": game_id,
            "game_name": game_name,
            "api_type": api_type
        }
        
        # Store in fake_door_interactions table
        insert_sql = """INSERT INTO fake_door_interactions (user_id, interaction_type, context, metadata)
                       VALUES (?, ?, ?, ?)"""
        if DB_TYPE == "postgres":
            insert_sql = insert_sql.replace("?", "%s")
        
        execute_query(
            ENGINE_CONN,
            insert_sql,
            (
                user_id,
                "image_upload",
                json.dumps(interaction_context),
                json.dumps(metadata)
            )
        )
        ENGINE_CONN.commit()
        
        logger.info(f"Stored image upload fake-door interaction for user {user_id}, game_id: {game_id}")
        
        # Return success message (fake-door)
        game_name_text = f" for {game_name}" if game_name else ""
        return {
            "success": True,
            "message": f"Thank you for your interest! Image upload functionality{game_name_text} is coming soon. We've recorded your request and will notify you when it's available.",
            "fake_door": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing image upload interaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")


class RulesExplainRequest(BaseModel):
    game_id: int
    context: Optional[str] = None

@app.post("/rules/explain")
def explain_rules(
    req: RulesExplainRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Fake-door: Store rules explainer interaction for later analysis."""
    user_id = current_user["id"] if current_user else None
    logger.info(f"Rules explainer fake-door request from user: {user_id or 'anonymous'}, game_id: {req.game_id}")
    
    try:
        # Get game name for context
        game_name = None
        try:
            cur = execute_query(ENGINE_CONN, "SELECT name FROM games WHERE id = ?", (req.game_id,))
            row = cur.fetchone()
            if row:
                game_name = row[0]
        except:
            pass
        
        # Store interaction data
        interaction_context = {
            "game_id": req.game_id,
            "game_name": game_name,
            "context": req.context,
            "user_id": user_id
        }
        
        metadata = {
            "game_id": req.game_id,
            "game_name": game_name
        }
        
        # Store in fake_door_interactions table
        insert_sql = """INSERT INTO fake_door_interactions (user_id, interaction_type, context, metadata)
                       VALUES (?, ?, ?, ?)"""
        if DB_TYPE == "postgres":
            insert_sql = insert_sql.replace("?", "%s")
        
        execute_query(
            ENGINE_CONN,
            insert_sql,
            (
                user_id,
                "rules_explainer",
                json.dumps(interaction_context),
                json.dumps(metadata)
            )
        )
        ENGINE_CONN.commit()
        
        logger.info(f"Stored rules explainer fake-door interaction for user {user_id}, game_id: {req.game_id}")
        
        # Return success message (fake-door)
        return {
            "success": True,
            "message": f"Thank you for your interest! Rules explainer for {game_name or f'game {req.game_id}'} is coming soon. We've recorded your request and will notify you when it's available.",
            "fake_door": True
        }
        
    except Exception as e:
        logger.error(f"Error storing rules explainer interaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")


# Scoring endpoints
class ScoringPadRequest(BaseModel):
    game_id: int
    context: Optional[str] = None

class CalculateScoreRequest(BaseModel):
    game_id: int
    mechanism_id: int
    intermediate_scores: Dict[str, Any]  # Dictionary of score_id -> value

class SaveScoringSessionRequest(BaseModel):
    game_id: int
    mechanism_id: int
    intermediate_scores: Dict[str, Any]
    final_score: Optional[float] = None

@app.post("/scoring/pad")
def open_scoring_pad(
    req: ScoringPadRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Fake-door: Store scoring pad interaction for later analysis."""
    user_id = current_user["id"] if current_user else None
    logger.info(f"Scoring pad fake-door request from user: {user_id or 'anonymous'}, game_id: {req.game_id}")
    
    try:
        # Get game name for context
        game_name = None
        try:
            cur = execute_query(ENGINE_CONN, "SELECT name FROM games WHERE id = ?", (req.game_id,))
            row = cur.fetchone()
            if row:
                game_name = row[0]
        except:
            pass
        
        # Store interaction data
        interaction_context = {
            "game_id": req.game_id,
            "game_name": game_name,
            "context": req.context,
            "user_id": user_id
        }
        
        metadata = {
            "game_id": req.game_id,
            "game_name": game_name
        }
        
        # Store in fake_door_interactions table
        insert_sql = """INSERT INTO fake_door_interactions (user_id, interaction_type, context, metadata)
                       VALUES (?, ?, ?, ?)"""
        if DB_TYPE == "postgres":
            insert_sql = insert_sql.replace("?", "%s")
        
        execute_query(
            ENGINE_CONN,
            insert_sql,
            (
                user_id,
                "scoring_pad",
                json.dumps(interaction_context),
                json.dumps(metadata)
            )
        )
        ENGINE_CONN.commit()
        
        logger.info(f"Stored scoring pad fake-door interaction for user {user_id}, game_id: {req.game_id}")
        
        # Return success message (fake-door)
        game_name_text = f" for {game_name}" if game_name else ""
        return {
            "success": True,
            "message": f"Thank you for your interest! End-game scoring{game_name_text} is coming soon. We've recorded your request and will notify you when it's available.",
            "fake_door": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing scoring pad interaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")


@app.get("/scoring/mechanism/{game_id}")
def get_scoring_mechanism(
    game_id: int,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get the approved scoring mechanism for a game."""
    try:
        # Get approved mechanism for this game
        query = """SELECT id, criteria_json, created_at 
                   FROM scoring_mechanisms 
                   WHERE game_id = ? AND status = 'approved'
                   ORDER BY created_at DESC LIMIT 1"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        
        cur = execute_query(ENGINE_CONN, query, (game_id,))
        row = cur.fetchone()
        
        if not row:
            return {
                "exists": False,
                "mechanism": None
            }
        
        mechanism_id = row[0]
        criteria_json = row[1]
        
        try:
            criteria = json.loads(criteria_json)
        except:
            criteria = {}
        
        return {
            "exists": True,
            "mechanism": {
                "id": mechanism_id,
                "game_id": game_id,
                "criteria": criteria,
                "created_at": row[2].isoformat() if hasattr(row[2], 'isoformat') else str(row[2])
            }
        }
    except Exception as e:
        logger.error(f"Error getting scoring mechanism: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get scoring mechanism: {str(e)}")


@app.post("/scoring/calculate")
def calculate_score(
    req: CalculateScoreRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Calculate final score from intermediate scores."""
    user_id = current_user["id"] if current_user else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Get the scoring mechanism
        query = """SELECT criteria_json FROM scoring_mechanisms 
                   WHERE id = ? AND status = 'approved'"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        
        cur = execute_query(ENGINE_CONN, query, (req.mechanism_id,))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Scoring mechanism not found or not approved")
        
        criteria = json.loads(row[0])
        intermediate_scores_list = criteria.get("intermediate_scores", [])
        
        # Calculate intermediate scores
        calculated_intermediates = []
        total_score = 0.0
        
        for score_def in intermediate_scores_list:
            score_id = score_def.get("id")
            label = score_def.get("label", "")
            formula = score_def.get("formula", "value")
            input_value = req.intermediate_scores.get(score_id, 0)
            
            # Simple formula evaluation (can be extended)
            if formula == "value":
                calculated_value = float(input_value)
            elif formula.startswith("value *") or formula.startswith("value*"):
                multiplier = float(formula.split("*")[-1].strip())
                calculated_value = float(input_value) * multiplier
            elif "*" in formula:
                # Try to extract multiplier
                parts = formula.split("*")
                if len(parts) == 2:
                    try:
                        multiplier = float(parts[1].strip())
                        calculated_value = float(input_value) * multiplier
                    except:
                        calculated_value = float(input_value)
                else:
                    calculated_value = float(input_value)
            else:
                calculated_value = float(input_value)
            
            calculated_intermediates.append({
                "id": score_id,
                "label": label,
                "value": calculated_value,
                "input_value": input_value
            })
            total_score += calculated_value
        
        # Apply final score formula
        final_formula = criteria.get("final_score_formula", "sum")
        if final_formula == "sum":
            final_score = total_score
        else:
            final_score = total_score  # Default to sum
        
        return {
            "success": True,
            "intermediate_scores": calculated_intermediates,
            "final_score": final_score
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate score: {str(e)}")


@app.post("/scoring/save")
def save_scoring_session(
    req: SaveScoringSessionRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Save a scoring session for a user."""
    user_id = current_user["id"] if current_user else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Calculate final score if not provided
        final_score = req.final_score
        if final_score is None:
            # Sum all intermediate scores
            final_score = sum(float(v) for v in req.intermediate_scores.values())
        
        # Save to database
        insert_sql = """INSERT INTO user_scoring_sessions 
                       (user_id, game_id, mechanism_id, intermediate_scores_json, final_score, updated_at)
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)"""
        if DB_TYPE == "postgres":
            insert_sql = insert_sql.replace("?", "%s")
        
        execute_query(
            ENGINE_CONN,
            insert_sql,
            (
                user_id,
                req.game_id,
                req.mechanism_id,
                json.dumps(req.intermediate_scores),
                final_score
            )
        )
        ENGINE_CONN.commit()
        
        return {
            "success": True,
            "message": "Scoring session saved successfully"
        }
    except Exception as e:
        logger.error(f"Error saving scoring session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save scoring session: {str(e)}")


# Admin endpoints for scoring mechanism review
class ReviewScoringMechanismRequest(BaseModel):
    mechanism_id: int
    status: str  # 'approved' or 'rejected'
    review_notes: Optional[str] = None

@app.post("/admin/scoring/parse-rulebook")
def parse_rulebook_for_scoring(
    game_id: int,
    rulebook_text: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Parse a rulebook and create a pending scoring mechanism. Admin only."""
    try:
        from backend.rulebook_parser import extract_scoring_from_rulebook
        
        # Extract scoring mechanism
        mechanism_data = extract_scoring_from_rulebook(game_id, rulebook_text)
        
        if not mechanism_data:
            return {
                "success": False,
                "message": "Could not extract scoring criteria from rulebook. Confidence too low or no criteria found."
            }
        
        # Check if mechanism already exists for this game
        check_query = """SELECT id FROM scoring_mechanisms WHERE game_id = ? AND status = 'pending'"""
        if DB_TYPE == "postgres":
            check_query = check_query.replace("?", "%s")
        
        cur = execute_query(ENGINE_CONN, check_query, (game_id,))
        existing = cur.fetchone()
        
        if existing:
            # Update existing pending mechanism
            update_query = """UPDATE scoring_mechanisms 
                             SET criteria_json = ?, created_at = CURRENT_TIMESTAMP
                             WHERE id = ?"""
            if DB_TYPE == "postgres":
                update_query = update_query.replace("?", "%s")
            
            execute_query(ENGINE_CONN, update_query, (mechanism_data["criteria_json"], existing[0]))
            mechanism_id = existing[0]
        else:
            # Insert new mechanism
            insert_query = """INSERT INTO scoring_mechanisms (game_id, criteria_json, status)
                             VALUES (?, ?, ?)"""
            if DB_TYPE == "postgres":
                insert_query = insert_query.replace("?", "%s")
            
            cur = execute_query(ENGINE_CONN, insert_query, (
                game_id,
                mechanism_data["criteria_json"],
                "pending"
            ))
            ENGINE_CONN.commit()
            
            # Get the inserted ID
            if DB_TYPE == "postgres":
                cur = execute_query(ENGINE_CONN, "SELECT LASTVAL()", ())
            else:
                cur = execute_query(ENGINE_CONN, "SELECT LAST_INSERT_ROWID()", ())
            mechanism_id = cur.fetchone()[0]
        
        ENGINE_CONN.commit()
        
        return {
            "success": True,
            "mechanism_id": mechanism_id,
            "confidence": mechanism_data.get("confidence", 0.0),
            "message": "Scoring mechanism created and pending review"
        }
    except Exception as e:
        logger.error(f"Error parsing rulebook for scoring: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse rulebook: {str(e)}")


@app.get("/admin/scoring/pending")
def get_pending_scoring_mechanisms(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Get all pending scoring mechanisms for admin review. Admin only."""
    try:
        query = """SELECT sm.id, sm.game_id, g.name as game_name, sm.criteria_json, sm.created_at
                   FROM scoring_mechanisms sm
                   JOIN games g ON g.id = sm.game_id
                   WHERE sm.status = 'pending'
                   ORDER BY sm.created_at DESC"""
        
        cur = execute_query(ENGINE_CONN, query, ())
        mechanisms = []
        
        for row in cur.fetchall():
            try:
                criteria = json.loads(row[3])
            except:
                criteria = {}
            
            mechanisms.append({
                "id": row[0],
                "game_id": row[1],
                "game_name": row[2],
                "criteria": criteria,
                "created_at": row[4].isoformat() if hasattr(row[4], 'isoformat') else str(row[4])
            })
        
        return {
            "success": True,
            "mechanisms": mechanisms
        }
    except Exception as e:
        logger.error(f"Error getting pending scoring mechanisms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get pending mechanisms: {str(e)}")


@app.post("/admin/scoring/review")
def review_scoring_mechanism(
    req: ReviewScoringMechanismRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Review and approve/reject a scoring mechanism. Admin only."""
    if req.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
    
    try:
        admin_user_id = current_user["id"]
        
        # If approving, check if there's already an approved mechanism for this game
        if req.status == "approved":
            # Get game_id from mechanism
            get_game_query = "SELECT game_id FROM scoring_mechanisms WHERE id = ?"
            if DB_TYPE == "postgres":
                get_game_query = get_game_query.replace("?", "%s")
            
            cur = execute_query(ENGINE_CONN, get_game_query, (req.mechanism_id,))
            game_row = cur.fetchone()
            
            if not game_row:
                raise HTTPException(status_code=404, detail="Scoring mechanism not found")
            
            game_id = game_row[0]
            
            # Check for existing approved mechanism
            check_query = """SELECT id FROM scoring_mechanisms 
                           WHERE game_id = ? AND status = 'approved' AND id != ?"""
            if DB_TYPE == "postgres":
                check_query = check_query.replace("?", "%s")
            
            cur = execute_query(ENGINE_CONN, check_query, (game_id, req.mechanism_id))
            existing = cur.fetchone()
            
            if existing:
                # Reject the old approved mechanism
                update_old_query = """UPDATE scoring_mechanisms 
                                     SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, 
                                         reviewed_by = ?, review_notes = 'Replaced by new approved mechanism'
                                     WHERE id = ?"""
                if DB_TYPE == "postgres":
                    update_old_query = update_old_query.replace("?", "%s")
                
                execute_query(ENGINE_CONN, update_old_query, (admin_user_id, existing[0]))
        
        # Update the mechanism status
        update_query = """UPDATE scoring_mechanisms 
                         SET status = ?, reviewed_at = CURRENT_TIMESTAMP, 
                             reviewed_by = ?, review_notes = ?
                         WHERE id = ?"""
        if DB_TYPE == "postgres":
            update_query = update_query.replace("?", "%s")
        
        execute_query(ENGINE_CONN, update_query, (
            req.status,
            admin_user_id,
            req.review_notes,
            req.mechanism_id
        ))
        ENGINE_CONN.commit()
        
        return {
            "success": True,
            "message": f"Scoring mechanism {req.status} successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing scoring mechanism: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to review mechanism: {str(e)}")


@app.get("/games/{game_id}/features")
def get_game_features_endpoint(game_id: int, current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)):
    """Get all features for a game, including original and modifications. Admin only."""
    try:
        # Get original features
        features = get_game_features(ENGINE_CONN, game_id)
        
        # Get feature modifications
        query = """SELECT feature_type, feature_id, action 
               FROM feature_mods 
               WHERE game_id = ? 
               ORDER BY created_at DESC"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (game_id,))
        mods = cur.fetchall()
        
        # Apply modifications to get final feature set
        final_features = {
            "mechanics": set(features.get("mechanics", set())),
            "categories": set(features.get("categories", set())),
            "designers": set(features.get("designers", set())),
            "artists": set(features.get("artists", set())),
            "publishers": set(features.get("publishers", set())),
            "families": set(features.get("families", set())),
        }
        
        # Get all available features for each type
        available_features = {}
        for feature_type in ["mechanics", "categories", "designers", "artists", "publishers", "families"]:
            table_name = feature_type if feature_type != "families" else "families"
            query = f"SELECT id, name FROM {table_name} ORDER BY name"
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
            cur = execute_query(ENGINE_CONN, query)
            available_features[feature_type] = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
        
        # Apply modifications
        for mod in mods:
            feature_type = mod[0]
            feature_id = mod[1]
            action = mod[2]
            
            # Find feature name
            table_name = feature_type if feature_type != "families" else "families"
            query = f"SELECT name FROM {table_name} WHERE id = ?"
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
            cur = execute_query(ENGINE_CONN, query, (feature_id,))
            row = cur.fetchone()
            if row:
                feature_name = row[0]
                if action == "add":
                    final_features[feature_type].add(feature_name)
                elif action == "remove":
                    final_features[feature_type].discard(feature_name)
        
        return {
            "game_id": game_id,
            "original_features": {
                "mechanics": list(features.get("mechanics", set())),
                "categories": list(features.get("categories", set())),
                "designers": list(features.get("designers", set())),
                "artists": list(features.get("artists", set())),
                "publishers": list(features.get("publishers", set())),
                "families": list(features.get("families", set())),
            },
            "final_features": {
                "mechanics": list(final_features["mechanics"]),
                "categories": list(final_features["categories"]),
                "designers": list(final_features["designers"]),
                "artists": list(final_features["artists"]),
                "publishers": list(final_features["publishers"]),
                "families": list(final_features["families"]),
            },
            "modifications": [{"feature_type": m[0], "feature_id": m[1], "action": m[2]} for m in mods],
            "available_features": available_features,
        }
    except Exception as e:
        logger.error(f"Error getting game features: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get game features: {str(e)}")


@app.post("/games/{game_id}/features/modify")
def modify_game_features(
    game_id: int,
    feature_type: str,
    feature_id: int,
    action: str,  # 'add' or 'remove'
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Add or remove a feature modification for a game."""
    if action not in ["add", "remove"]:
        raise HTTPException(status_code=400, detail="Action must be 'add' or 'remove'")
    
    if feature_type not in ["mechanics", "categories", "designers", "artists", "publishers", "families"]:
        raise HTTPException(status_code=400, detail="Invalid feature type")
    
    try:
        # Verify game exists
        query = "SELECT id FROM games WHERE id = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (game_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Verify feature exists
        table_name = feature_type if feature_type != "families" else "families"
        query = f"SELECT id FROM {table_name} WHERE id = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (feature_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Check if modification already exists
        query = """SELECT id FROM feature_mods 
               WHERE game_id = ? AND feature_type = ? AND feature_id = ? AND action = ?"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (game_id, feature_type, feature_id, action))
        existing = cur.fetchone()
        
        if existing:
            # Modification already exists, return success
            return {"success": True, "message": "Modification already exists"}
        
        # Remove opposite action if it exists
        opposite_action = "remove" if action == "add" else "add"
        query = """DELETE FROM feature_mods 
               WHERE game_id = ? AND feature_type = ? AND feature_id = ? AND action = ?"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        execute_query(ENGINE_CONN, query, (game_id, feature_type, feature_id, opposite_action))
        
        # Add new modification
        query = """INSERT INTO feature_mods (game_id, feature_type, feature_id, action)
               VALUES (?, ?, ?, ?)"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        execute_query(ENGINE_CONN, query, (game_id, feature_type, feature_id, action))
        ENGINE_CONN.commit()
        
        return {"success": True, "message": f"Feature {action}ed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error modifying game features: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to modify features: {str(e)}")


@app.delete("/games/{game_id}/features/modify/{mod_id}")
def remove_feature_modification(
    game_id: int,
    mod_id: int,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Remove a feature modification."""
    try:
        cur = execute_query(
            ENGINE_CONN,
            "DELETE FROM feature_mods WHERE id = ? AND game_id = ?",
            (mod_id, game_id)
        )
        ENGINE_CONN.commit()
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Modification not found")
        
        return {"success": True, "message": "Modification removed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing feature modification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to remove modification: {str(e)}")


@app.get("/marketplace/search")
def search_marketplace_endpoint(
    game_id: int,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Search marketplace listings for a game from multiple sources.
    Returns aggregated results from Amazon, eBay, GeekMarket, and Wallapop.
    Use USE_MOCK_MARKETPLACE environment variable to toggle mock mode.
    """
    try:
        import os
        from backend.marketplace_service import search_marketplace
        
        # Get game name for search
        cur = execute_query(ENGINE_CONN, "SELECT name FROM games WHERE id = ?", (game_id,))
        game_row = cur.fetchone()
        if not game_row:
            raise HTTPException(status_code=404, detail="Game not found")
        
        game_name = game_row[0]
        
        # Search all marketplaces
        listings = search_marketplace(game_name)
        
        return {
            "game_id": game_id,
            "game_name": game_name,
            "listings": listings,
            "total": len(listings),
            "mock_mode": os.getenv("USE_MOCK_MARKETPLACE", "false").lower() == "true"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching marketplace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search marketplace: {str(e)}")


@app.get("/feedback/questions/random")
def get_random_feedback_question(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get a random active feedback question with its options."""
    try:
        # Use RANDOM() for SQLite, RANDOM() for PostgreSQL (both support it)
        query = """SELECT id, question_text, question_type 
               FROM feedback_questions 
               WHERE is_active = ? 
               ORDER BY RANDOM() 
               LIMIT 1"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
            cur = execute_query(ENGINE_CONN, query, (True,))
        else:
            cur = execute_query(ENGINE_CONN, query, (1,))
        row = cur.fetchone()
        
        if not row:
            return None
        
        question_id = row[0]
        
        # Get options for this question with their IDs
        cur = execute_query(
            ENGINE_CONN,
            """SELECT id, option_text FROM feedback_question_options 
               WHERE question_id = ? 
               ORDER BY display_order, id""",
            (question_id,)
        )
        options = [{"id": opt[0], "text": opt[1]} for opt in cur.fetchall()]
        
        return {
            "id": question_id,
            "question_text": row[1],
            "question_type": row[2],
            "options": options if options else None
        }
    except Exception as e:
        logger.error(f"Error getting feedback question: {e}", exc_info=True)
        return None


@app.get("/feedback/questions/helpful")
def get_helpful_question(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get or create the 'Were these results helpful?' question with Yes/No options."""
    try:
        # Ensure transaction is clean before starting
        if DB_TYPE == "postgres":
            try:
                ENGINE_CONN.rollback()
            except:
                pass  # Ignore if no transaction in progress
        
        # Try to find existing question
        query = """SELECT id FROM feedback_questions 
               WHERE question_text = 'Were these results helpful?' 
               LIMIT 1"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query)
        row = cur.fetchone()
        
        if row:
            question_id = row[0]
        else:
            # Create the question if it doesn't exist
            query = """INSERT INTO feedback_questions (question_text, question_type, is_active)
                   VALUES (?, ?, ?)"""
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s") + " RETURNING id"
                cur = execute_query(ENGINE_CONN, query, ("Were these results helpful?", "single_select", True))
                question_id = cur.fetchone()[0]
            else:
                cur = execute_query(ENGINE_CONN, query, ("Were these results helpful?", "single_select", 1))
                question_id = cur.lastrowid
            ENGINE_CONN.commit()
        
        # Always ensure Yes and No options exist (regardless of whether question was just created)
        # Use a more robust approach: try to insert, ignore errors if they already exist
        options_to_insert = [("Yes", 0), ("No", 1)]
        for option_text, display_order in options_to_insert:
            try:
                if DB_TYPE == "postgres":
                    # For PostgreSQL, check first, then insert if not exists
                    query_check = """SELECT id FROM feedback_question_options 
                                  WHERE question_id = %s AND option_text = %s"""
                    cur = execute_query(ENGINE_CONN, query_check, (question_id, option_text))
                    existing = cur.fetchone()
                    if not existing:
                        query = """INSERT INTO feedback_question_options (question_id, option_text, display_order)
                                   VALUES (%s, %s, %s)"""
                        execute_query(ENGINE_CONN, query, (question_id, option_text, display_order))
                        ENGINE_CONN.commit()
                        logger.info(f"Inserted '{option_text}' option for question {question_id}")
                else:
                    # For SQLite, check first, then insert if not exists
                    query_check = """SELECT id FROM feedback_question_options 
                                  WHERE question_id = ? AND option_text = ?"""
                    cur = execute_query(ENGINE_CONN, query_check, (question_id, option_text))
                    existing = cur.fetchone()
                    if not existing:
                        query = """INSERT INTO feedback_question_options (question_id, option_text, display_order)
                                   VALUES (?, ?, ?)"""
                        execute_query(ENGINE_CONN, query, (question_id, option_text, display_order))
                        ENGINE_CONN.commit()
                        logger.info(f"Inserted '{option_text}' option for question {question_id}")
            except Exception as e:
                # If insert fails, that's okay - option may already exist or there's a constraint
                logger.warning(f"Could not insert '{option_text}' option for question {question_id} (may already exist): {e}")
                try:
                    ENGINE_CONN.rollback()
                except:
                    pass
        
        # Get options with their IDs
        query = """SELECT id, option_text FROM feedback_question_options 
               WHERE question_id = ? 
               ORDER BY display_order, id"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (question_id,))
        options = [{"id": opt[0], "text": opt[1]} for opt in cur.fetchall()]
        
        return {
            "id": question_id,
            "question_text": "Were these results helpful?",
            "question_type": "single_select",
            "options": options
        }
    except Exception as e:
        logger.error(f"Error getting helpful question: {e}", exc_info=True)
        return None


@app.post("/feedback/respond")
def submit_feedback_response(
    req: FeedbackResponseRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_required)
):
    """Submit a feedback response.
    For single_select questions, use option_id.
    For multi_select questions, response should be JSON array of option IDs.
    For text questions, use response."""
    try:
        question_type = None
        question_id = req.question_id
        option_id = req.option_id
        response = req.response
        context = req.context
        thread_id = req.thread_id
        
        logger.debug(f"Feedback response: question_id={question_id}, option_id={option_id}, response={response}, context={context}, thread_id={thread_id}, user_id={current_user['id']}")
        
        # Verify question exists if provided
        if question_id is not None:
            query = "SELECT id, question_type FROM feedback_questions WHERE id = ? AND is_active = ?"
            if DB_TYPE == "postgres":
                query = query.replace("?", "%s")
                cur = execute_query(ENGINE_CONN, query, (question_id, True))
            else:
                cur = execute_query(ENGINE_CONN, query, (question_id, 1))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Question not found")
            
            question_type = row[1]
            
            # For single_select, verify option_id exists and belongs to this question
            if question_type == "single_select":
                if option_id is None:
                    raise HTTPException(status_code=400, detail="option_id required for single_select questions")
                query = "SELECT id FROM feedback_question_options WHERE id = ? AND question_id = ?"
                if DB_TYPE == "postgres":
                    query = query.replace("?", "%s")
                cur = execute_query(ENGINE_CONN, query, (option_id, question_id))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Option not found or doesn't belong to question")
            # For multi_select, response should contain JSON array of option IDs
            elif question_type == "multi_select":
                if not response:
                    raise HTTPException(status_code=400, detail="response required for multi_select questions (should be JSON array of option IDs)")
                try:
                    option_ids = json.loads(response)
                    if not isinstance(option_ids, list):
                        raise HTTPException(status_code=400, detail="response must be a JSON array for multi_select questions")
                    # Verify all option IDs exist and belong to this question
                    for opt_id in option_ids:
                        query = "SELECT id FROM feedback_question_options WHERE id = ? AND question_id = ?"
                        if DB_TYPE == "postgres":
                            query = query.replace("?", "%s")
                        cur = execute_query(ENGINE_CONN, query, (opt_id, question_id))
                        if not cur.fetchone():
                            raise HTTPException(status_code=404, detail=f"Option {opt_id} not found or doesn't belong to question")
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON in response for multi_select question")
        
        # For multi_select, create one response record per selected option
        if question_type == "multi_select" and response:
            try:
                option_ids = json.loads(response)
                for opt_id in option_ids:
                    insert_sql = """INSERT INTO user_feedback_responses 
                           (user_id, question_id, option_id, response, context, thread_id)
                           VALUES (?, ?, ?, ?, ?, ?)"""
                    if DB_TYPE == "postgres":
                        insert_sql = insert_sql.replace("?", "%s")
                    try:
                        execute_query(
                            ENGINE_CONN,
                            insert_sql,
                            (
                                int(current_user["id"]), 
                                question_id, 
                                opt_id,  # Each option gets its own record
                                None,  # response field is None for multi_select (option_id is used)
                                context if context is not None else None, 
                                thread_id if thread_id is not None else None
                            )
                        )
                    except Exception as e:
                        # Handle sequence sync issues for PostgreSQL
                        is_unique_violation = False
                        if DB_TYPE == "postgres":
                            if psycopg2 and psycopg2.errors:
                                is_unique_violation = isinstance(e, psycopg2.errors.UniqueViolation)
                            else:
                                is_unique_violation = "UniqueViolation" in str(type(e).__name__) or "duplicate key" in str(e).lower()
                        
                        if is_unique_violation:
                            logger.warning(f"Sequence out of sync for user_feedback_responses, fixing: {e}")
                            try:
                                # Fix the sequence by setting it to max(id) + 1
                                fix_seq_query = "SELECT setval('user_feedback_responses_id_seq', COALESCE((SELECT MAX(id) FROM user_feedback_responses), 0) + 1, false)"
                                execute_query(ENGINE_CONN, fix_seq_query)
                                ENGINE_CONN.commit()
                                # Retry the insert
                                execute_query(
                                    ENGINE_CONN,
                                    insert_sql,
                                    (
                                        int(current_user["id"]), 
                                        question_id, 
                                        opt_id,
                                        None,
                                        context if context is not None else None, 
                                        thread_id if thread_id is not None else None
                                    )
                                )
                                logger.info(f"Fixed sequence and inserted feedback response for user {current_user['id']}")
                            except Exception as retry_error:
                                logger.error(f"Failed to fix sequence and retry insert: {retry_error}", exc_info=True)
                                raise
                        else:
                            raise
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in response")
        else:
            # For single_select or text, create a single response record
            # Ensure all fields are properly set
            # If additional_details is provided, append it to response
            final_response = response
            if req.additional_details and req.additional_details.strip():
                if final_response:
                    final_response = f"{final_response}\n\nAdditional details: {req.additional_details}"
                else:
                    final_response = req.additional_details
            
            logger.debug(f"Inserting feedback: user_id={int(current_user['id'])}, question_id={question_id}, option_id={option_id}, response={final_response}, context={context}, thread_id={thread_id}")
            insert_sql = """INSERT INTO user_feedback_responses 
                   (user_id, question_id, option_id, response, context, thread_id)
                   VALUES (?, ?, ?, ?, ?, ?)"""
            if DB_TYPE == "postgres":
                insert_sql = insert_sql.replace("?", "%s")
            try:
                execute_query(
                    ENGINE_CONN,
                    insert_sql,
                    (
                        int(current_user["id"]),  # Ensure user_id is int
                        question_id,
                        option_id,
                        final_response,
                        context,
                        thread_id
                    )
                )
            except Exception as e:
                # Handle sequence sync issues for PostgreSQL
                is_unique_violation = False
                if DB_TYPE == "postgres":
                    if psycopg2 and psycopg2.errors:
                        is_unique_violation = isinstance(e, psycopg2.errors.UniqueViolation)
                    else:
                        is_unique_violation = "UniqueViolation" in str(type(e).__name__) or "duplicate key" in str(e).lower()
                
                if is_unique_violation:
                    logger.warning(f"Sequence out of sync for user_feedback_responses, fixing: {e}")
                    try:
                        # Fix the sequence by setting it to max(id) + 1
                        fix_seq_query = "SELECT setval('user_feedback_responses_id_seq', COALESCE((SELECT MAX(id) FROM user_feedback_responses), 0) + 1, false)"
                        execute_query(ENGINE_CONN, fix_seq_query)
                        ENGINE_CONN.commit()
                        # Retry the insert
                        execute_query(
                            ENGINE_CONN,
                            insert_sql,
                            (
                                int(current_user["id"]),
                                question_id,
                                option_id,
                                final_response,
                                context,
                                thread_id
                            )
                        )
                        logger.info(f"Fixed sequence and inserted feedback response for user {current_user['id']}")
                    except Exception as retry_error:
                        logger.error(f"Failed to fix sequence and retry insert: {retry_error}", exc_info=True)
                        raise
                else:
                    raise
            
            # Handle A/B test preferences
            # If this is a "No" or dislike response to an A/B test question, clear the preference
            if question_id:
                # Check if this is an A/B test question by checking if it's linked to an ab_test_config
                cur_check = execute_query(
                    ENGINE_CONN,
                    """SELECT fq.question_text FROM feedback_questions fq 
                       WHERE fq.id = ?""",
                    (question_id,)
                )
                question_row = cur_check.fetchone()
                if question_row:
                    question_text = question_row[0] if question_row else ""
                    # Check if this looks like an A/B test question (contains "prefer" or "which")
                    is_ab_question = "prefer" in question_text.lower() or "which" in question_text.lower()
                    
                    # Check if this is a "No" or negative response
                    if option_id:
                        cur_opt = execute_query(
                            ENGINE_CONN,
                            """SELECT option_text FROM feedback_question_options 
                               WHERE id = ?""",
                            (option_id,)
                        )
                        opt_row = cur_opt.fetchone()
                        if opt_row:
                            option_text = opt_row[0] if opt_row else ""
                            is_negative = option_text.lower() in ["no", "dislike", "neither", "none"]
                            
                            if is_ab_question and is_negative:
                                # Clear A/B test preference for this user
                                # Find the config_key from the question context or option
                                # For now, we'll clear all A/B preferences when user says No
                                # This is a simplified approach - in production you might want to track which config
                                execute_query(
                                    ENGINE_CONN,
                                    """DELETE FROM user_ab_preferences WHERE user_id = ?""",
                                    (int(current_user["id"]),)
                                )
                                ENGINE_CONN.commit()
                                logger.info(f"Cleared A/B test preferences for user {current_user['id']} after negative feedback")
            
            # If this is a positive response to an A/B test (user selected A or B), store preference
            if question_id and option_id:
                cur_ab_check = execute_query(
                    ENGINE_CONN,
                    """SELECT fq.question_text, fqo.option_text 
                       FROM feedback_questions fq
                       JOIN feedback_question_options fqo ON fqo.id = ?
                       WHERE fq.id = ?""",
                    (option_id, question_id)
                )
                ab_row = cur_ab_check.fetchone()
                if ab_row:
                    ab_question_text = ab_row[0] if ab_row else ""
                    ab_option_text = ab_row[1] if ab_row else ""
                    
                    # Check if this is an A/B test question and user selected A or B
                    is_ab_question = "prefer" in ab_question_text.lower() or "which" in ab_question_text.lower()
                    is_positive = ab_option_text.lower() not in ["no", "dislike", "neither", "none"]
                    
                    if is_ab_question and is_positive:
                        # Try to extract config_key from context or question
                        # For now, we'll use a simple approach: check if option text matches A/B labels
                        # In production, you might want to store config_key in the question context
                        # For simplicity, we'll check all active A/B configs and see which one matches
                        cur_configs = execute_query(
                            ENGINE_CONN,
                            """SELECT config_key, config_value FROM ab_test_configs WHERE is_active = ?""",
                            (True if DB_TYPE == "postgres" else 1,)
                        )
                        for config_row in cur_configs.fetchall():
                            config_key = config_row[0]
                            try:
                                config_data = json.loads(config_row[1]) if isinstance(config_row[1], str) else config_row[1]
                                label_a = config_data.get("label_a", "Option A")
                                label_b = config_data.get("label_b", "Option B")
                                
                                # Determine which option was selected
                                if ab_option_text == label_a or "option a" in ab_option_text.lower():
                                    preferred_value = "A"
                                elif ab_option_text == label_b or "option b" in ab_option_text.lower():
                                    preferred_value = "B"
                                else:
                                    continue
                                
                                # Store or update preference
                                if DB_TYPE == "postgres":
                                    execute_query(
                                        ENGINE_CONN,
                                        """INSERT INTO user_ab_preferences (user_id, config_key, preferred_value)
                                           VALUES (%s, %s, %s)
                                           ON CONFLICT (user_id, config_key) 
                                           DO UPDATE SET preferred_value = EXCLUDED.preferred_value, updated_at = CURRENT_TIMESTAMP""",
                                        (int(current_user["id"]), config_key, preferred_value)
                                    )
                                else:
                                    # SQLite doesn't support ON CONFLICT with multiple columns easily
                                    # Check if exists first
                                    cur_exists = execute_query(
                                        ENGINE_CONN,
                                        """SELECT id FROM user_ab_preferences WHERE user_id = ? AND config_key = ?""",
                                        (int(current_user["id"]), config_key)
                                    )
                                    if cur_exists.fetchone():
                                        execute_query(
                                            ENGINE_CONN,
                                            """UPDATE user_ab_preferences 
                                               SET preferred_value = ?, updated_at = CURRENT_TIMESTAMP
                                               WHERE user_id = ? AND config_key = ?""",
                                            (preferred_value, int(current_user["id"]), config_key)
                                        )
                                    else:
                                        execute_query(
                                            ENGINE_CONN,
                                            """INSERT INTO user_ab_preferences (user_id, config_key, preferred_value)
                                               VALUES (?, ?, ?)""",
                                            (int(current_user["id"]), config_key, preferred_value)
                                        )
                                
                                ENGINE_CONN.commit()
                                logger.info(f"Stored A/B test preference for user {current_user['id']}: {config_key} = {preferred_value}")
                                break  # Only store for first matching config
                            except Exception as e:
                                logger.warning(f"Error processing A/B config for preference: {e}")
                                continue
        
        ENGINE_CONN.commit()
        
        # Verify the record was inserted
        cur = execute_query(
            ENGINE_CONN,
            "SELECT id, user_id, question_id, option_id, response, context, thread_id FROM user_feedback_responses WHERE id = (SELECT MAX(id) FROM user_feedback_responses WHERE user_id = ?)",
            (int(current_user["id"]),)
        )
        inserted_record = cur.fetchone()
        if inserted_record:
            logger.info(f"Feedback response saved: id={inserted_record[0]}, user_id={inserted_record[1]}, question_id={inserted_record[2]}, option_id={inserted_record[3]}, response={inserted_record[4]}, context={inserted_record[5]}, thread_id={inserted_record[6]}")
        else:
            logger.warning("Feedback response inserted but could not verify")
        
        return {"success": True, "message": "Feedback submitted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@app.get("/admin/games")
def get_all_games(
    page: int = 1,
    per_page: int = 50,
    search: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Get all games in database for admin use."""
    try:
        offset = (page - 1) * per_page
        
        if search:
            search_term = f"%{search}%"
            count_sql = "SELECT COUNT(*) FROM games WHERE name LIKE ?"
            count_params = (search_term,)
            sql = "SELECT id, name, year_published, thumbnail FROM games WHERE name LIKE ? ORDER BY name LIMIT ? OFFSET ?"
            params = (search_term, per_page, offset)
        else:
            count_sql = "SELECT COUNT(*) FROM games"
            count_params = ()
            sql = "SELECT id, name, year_published, thumbnail FROM games ORDER BY name LIMIT ? OFFSET ?"
            params = (per_page, offset)
        
        if DB_TYPE == "postgres":
            count_sql = count_sql.replace("?", "%s")
            sql = sql.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, count_sql, count_params)
        total = cur.fetchone()[0]
        
        cur = execute_query(ENGINE_CONN, sql, params)
        games = []
        for row in cur.fetchall():
            games.append({
                "id": row[0],
                "name": row[1],
                "year_published": row[2],
                "thumbnail": row[3]
            })
        
        return {
            "games": games,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    except Exception as e:
        logger.error(f"Error getting all games: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get games: {str(e)}")


# Admin endpoints for feedback questions
@app.get("/admin/feedback/questions")
def get_all_feedback_questions(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Get all feedback questions with their options."""
    try:
        query = """SELECT id, question_text, question_type, is_active, created_at 
               FROM feedback_questions 
               ORDER BY created_at DESC"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query)
        questions = []
        for row in cur.fetchall():
            question_id = row[0]
            # Get options for this question
            query_opts = """SELECT id, option_text, display_order 
                   FROM feedback_question_options 
                   WHERE question_id = ? 
                   ORDER BY display_order, id"""
            if DB_TYPE == "postgres":
                query_opts = query_opts.replace("?", "%s")
            cur_opts = execute_query(ENGINE_CONN, query_opts, (question_id,))
            options = [
                {"id": opt[0], "text": opt[1], "display_order": opt[2]}
                for opt in cur_opts.fetchall()
            ]
            questions.append({
                "id": question_id,
                "question_text": row[1],
                "question_type": row[2],
                "is_active": bool(row[3]),
                "created_at": row[4],
                "options": options
            })
        return {"questions": questions}
    except Exception as e:
        logger.error(f"Error getting feedback questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get feedback questions: {str(e)}")


@app.post("/admin/feedback/questions")
def create_feedback_question(
    req: FeedbackQuestionRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Create a new feedback question."""
    try:
        if req.question_type not in ["text", "single_select", "multi_select"]:
            raise HTTPException(status_code=400, detail="Invalid question type")
        
        # Insert question
        insert_sql = """INSERT INTO feedback_questions (question_text, question_type, is_active)
               VALUES (?, ?, ?)"""
        if DB_TYPE == "postgres":
            insert_sql = insert_sql.replace("?", "%s") + " RETURNING id"
        cur = execute_query(
            ENGINE_CONN,
            insert_sql,
            (req.question_text, req.question_type, 1 if req.is_active else 0)
        )
        if DB_TYPE == "postgres":
            question_id = cur.fetchone()[0]
        else:
            question_id = cur.lastrowid
        
        # Insert options if provided (for single_select or multi_select)
        if req.options and req.question_type in ["single_select", "multi_select"]:
            for idx, option_text in enumerate(req.options):
                if option_text.strip():  # Only insert non-empty options
                    execute_query(
                        ENGINE_CONN,
                        """INSERT INTO feedback_question_options (question_id, option_text, display_order)
                           VALUES (?, ?, ?)""",
                        (question_id, option_text, idx)
                    )
        
        ENGINE_CONN.commit()
        return {"success": True, "question_id": question_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating feedback question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create question: {str(e)}")


@app.put("/admin/feedback/questions/{question_id}")
def update_feedback_question(
    question_id: int,
    req: FeedbackQuestionRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Update a feedback question."""
    try:
        # Verify question exists
        query = "SELECT id FROM feedback_questions WHERE id = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query, (question_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Question not found")
        
        if req.question_type not in ["text", "single_select", "multi_select"]:
            raise HTTPException(status_code=400, detail="Invalid question type")
        
        # Update question fields
        query = """UPDATE feedback_questions 
               SET question_text = ?, question_type = ?, is_active = ?
               WHERE id = ?"""
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        execute_query(ENGINE_CONN, query, (req.question_text, req.question_type, 1 if req.is_active else 0, question_id))
        
        # Update options
        # Delete existing options
        query = "DELETE FROM feedback_question_options WHERE question_id = ?"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        execute_query(ENGINE_CONN, query, (question_id,))
        # Insert new options if provided (for single_select or multi_select)
        if req.options and req.question_type in ["single_select", "multi_select"]:
            for idx, option_text in enumerate(req.options):
                if option_text.strip():  # Only insert non-empty options
                    query = """INSERT INTO feedback_question_options (question_id, option_text, display_order)
                           VALUES (?, ?, ?)"""
                    if DB_TYPE == "postgres":
                        query = query.replace("?", "%s")
                    execute_query(ENGINE_CONN, query, (question_id, option_text, idx))
        
        ENGINE_CONN.commit()
        return {"success": True, "message": "Question updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feedback question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update question: {str(e)}")


def _get_or_create_ab_question(conn, config_key: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get or create a feedback question for an A/B test."""
    question_text = config_data.get("question_text", f"Which response do you prefer for {config_key}?")
    
    # Check if question already exists
    cur = execute_query(
        conn,
        "SELECT id FROM feedback_questions WHERE question_text = ? LIMIT 1",
        (question_text,)
    )
    row = cur.fetchone()
    
    if row:
        question_id = row[0]
    else:
        # Create new question
        # Use RETURNING for PostgreSQL, lastrowid for SQLite
        if DB_TYPE == "postgres":
            cur = execute_query(
                conn,
                """INSERT INTO feedback_questions (question_text, question_type, is_active)
                   VALUES (?, ?, ?) RETURNING id""",
                (question_text, "single_select", True)
            )
            question_id = cur.fetchone()[0]
            conn.commit()
        else:
            cur = execute_query(
                conn,
            """INSERT INTO feedback_questions (question_text, question_type, is_active)
               VALUES (?, ?, ?)""",
            (question_text, "single_select", 1)
        )
        question_id = cur.lastrowid
        conn.commit()
        
        # Create options
        label_a = config_data.get("label_a", "Option A")
        label_b = config_data.get("label_b", "Option B")
        
        execute_query(
            conn,
            """INSERT INTO feedback_question_options (question_id, option_text, display_order)
               VALUES (?, ?, ?)""",
            (question_id, label_a, 0)
        )
        execute_query(
            conn,
            """INSERT INTO feedback_question_options (question_id, option_text, display_order)
               VALUES (?, ?, ?)""",
            (question_id, label_b, 1)
        )
        conn.commit()
    
    # Get options
    cur = execute_query(
        conn,
        """SELECT id, option_text FROM feedback_question_options 
           WHERE question_id = ? ORDER BY display_order""",
        (question_id,)
    )
    options = [{"id": opt[0], "text": opt[1]} for opt in cur.fetchall()]
    
    return {
        "id": question_id,
        "question_text": question_text,
        "question_type": "single_select",
        "options": options
    }


@app.delete("/admin/feedback/questions/{question_id}")
def delete_feedback_question(
    question_id: int,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Delete a feedback question (and its options via CASCADE)."""
    try:
        cur = execute_query(ENGINE_CONN, "SELECT id FROM feedback_questions WHERE id = ?", (question_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Question not found")
        
        execute_query(ENGINE_CONN, "DELETE FROM feedback_questions WHERE id = ?", (question_id,))
        ENGINE_CONN.commit()
        return {"success": True, "message": "Question deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting feedback question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete question: {str(e)}")


# Admin endpoints for A/B test configs
@app.get("/admin/ab-test-configs")
def get_ab_test_configs(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Get all A/B test configurations."""
    try:
        query = "SELECT id, config_key, config_value, is_active, created_at, updated_at FROM ab_test_configs ORDER BY created_at DESC"
        if DB_TYPE == "postgres":
            query = query.replace("?", "%s")
        cur = execute_query(ENGINE_CONN, query)
        configs = []
        for row in cur.fetchall():
            try:
                config_value = json.loads(row[2])
            except:
                config_value = row[2]
            configs.append({
                "id": row[0],
                "config_key": row[1],
                "config_value": config_value,
                "is_active": bool(row[3]),
                "created_at": row[4],
                "updated_at": row[5],
            })
        return {"configs": configs}
    except Exception as e:
        logger.error(f"Error getting A/B test configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get A/B test configs: {str(e)}")


@app.post("/admin/ab-test-configs")
def create_ab_test_config(
    config_key: str,
    config_value: str,  # JSON string
    is_active: bool = False,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Create or update an A/B test configuration."""
    try:
        # Verify config_value is valid JSON
        try:
            json.loads(config_value)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="config_value must be valid JSON")
        
        # Check if config exists
        cur = execute_query(
            ENGINE_CONN,
            "SELECT id FROM ab_test_configs WHERE config_key = ?",
            (config_key,)
        )
        existing = cur.fetchone()
        
        if existing:
            # Update existing
            execute_query(
                ENGINE_CONN,
                """UPDATE ab_test_configs 
                   SET config_value = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE config_key = ?""",
                (config_value, 1 if is_active else 0, config_key)
            )
        else:
            # Create new
            execute_query(
                ENGINE_CONN,
                """INSERT INTO ab_test_configs (config_key, config_value, is_active)
                   VALUES (?, ?, ?)""",
                (config_key, config_value, 1 if is_active else 0)
            )
        
        ENGINE_CONN.commit()
        return {"success": True, "message": "A/B test config saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving A/B test config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save A/B test config: {str(e)}")


@app.put("/admin/ab-test-configs/{config_key}")
def update_ab_test_config(
    config_key: str,
    is_active: Optional[bool] = None,
    config_value: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Update an A/B test configuration."""
    try:
        updates = []
        params = []
        
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if config_value is not None:
            try:
                json.loads(config_value)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="config_value must be valid JSON")
            updates.append("config_value = ?")
            params.append(config_value)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(config_key)
        
        execute_query(
            ENGINE_CONN,
            f"UPDATE ab_test_configs SET {', '.join(updates)} WHERE config_key = ?",
            tuple(params)
        )
        ENGINE_CONN.commit()
        return {"success": True, "message": "A/B test config updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating A/B test config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update A/B test config: {str(e)}")


@app.delete("/admin/ab-test-configs/{config_key}")
def delete_ab_test_config(
    config_key: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Delete an A/B test configuration."""
    try:
        cur = execute_query(
            ENGINE_CONN,
            "SELECT id FROM ab_test_configs WHERE config_key = ?",
            (config_key,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Config not found")
        
        execute_query(ENGINE_CONN, "DELETE FROM ab_test_configs WHERE config_key = ?", (config_key,))
        ENGINE_CONN.commit()
        return {"success": True, "message": "A/B test config deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting A/B test config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete A/B test config: {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Check database connection
        if ENGINE_CONN:
            execute_query(ENGINE_CONN, "SELECT 1").fetchone()
        
        return {
            "status": "healthy",
            "database": "connected" if ENGINE_CONN else "not_initialized",
            "engine": "loaded" if ENGINE else "not_loaded"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 503

