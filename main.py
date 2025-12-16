# backend/app/main.py
from typing import Dict, Any, Optional, Set, List

import json
import sqlite3
from datetime import datetime

import faiss
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from db import db_connection, DB_PATH, ensure_schema
from backend.chat_nlu import interpret_message
from backend.similarity_engine import SimilarityEngine
from fastapi.middleware.cors import CORSMiddleware
from update_utils.export_name_id_map import get_name_id_map
# backend/app/main.py (add near top)
from backend.reasoning_utils import get_game_features, compute_meta_similarity, build_reason_summary
from backend.auth_utils import hash_password, verify_password, create_access_token, decode_access_token
from backend.logger_config import logger
from backend.bgg_collection import fetch_user_collection
from backend.image_processing import analyze_image, generate_prompt_from_analysis, generate_image
from backend.cache import get_cached, set_cached

import os
BASE_DIR = os.path.dirname(__file__)
index_path = os.path.join(BASE_DIR, "gen", "game_vectors.index")
SCHEMA_FILE = os.path.join(BASE_DIR, "update_utils", "schema.sql")


app = FastAPI(title="Pista Service")
security = HTTPBearer(auto_error=False)  # Make auth optional

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Globals for demo; for production you'd handle lifecycle more carefully.
ENGINE: Optional[SimilarityEngine] = None
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


class ChatResponse(BaseModel):
    reply_text: str
    results: Optional[List[Dict[str, Any]]] = None
    query_spec: Optional[Dict[str, Any]] = None
    thread_id: Optional[int] = None


class BggIdUpdateRequest(BaseModel):
    bgg_id: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    bgg_id: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
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
        
        # Verify user exists
        cur = ENGINE_CONN.execute("SELECT id, username, bgg_id, is_admin FROM users WHERE id = ?", (int(user_id),))
        user = cur.fetchone()
        if user is None:
            return None
        return {
            "id": user[0], 
            "username": user[1], 
            "bgg_id": user[2] if len(user) > 2 else None,
            "is_admin": bool(user[3] if len(user) > 3 else 0)
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
    cur = ENGINE_CONN.execute("SELECT is_admin FROM users WHERE id = ?", (user["id"],))
    row = cur.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def load_user_collection(user_id: str) -> Set[int]:
    """Load user's collection BGG IDs from database."""
    if not ENGINE_CONN:
        return set()
    try:
        cur = ENGINE_CONN.execute(
            "SELECT game_id FROM user_collections WHERE user_id = ?",
            (int(user_id),)
        )
        return {row[0] for row in cur.fetchall()}
    except (ValueError, sqlite3.Error):
        return set()


@app.on_event("startup")
def on_startup() -> None:
    global ENGINE, ENGINE_CONN
    logger.info("Starting Pista service...")
    ENGINE_CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
    ENGINE_CONN.row_factory = sqlite3.Row
    ensure_schema(ENGINE_CONN, SCHEMA_FILE)
    logger.info("Database schema ensured")
    
    # Migrate bgg_id column from INTEGER to TEXT if needed
    # SQLite doesn't support DROP COLUMN, so we use a workaround
    try:
        cur = ENGINE_CONN.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cur.fetchall()}
        if 'bgg_id' in columns and columns['bgg_id'].upper() == 'INTEGER':
            logger.info("Migrating bgg_id column from INTEGER to TEXT")
            # Create new table with TEXT column
            ENGINE_CONN.execute("""
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    bgg_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Copy data, converting INTEGER to TEXT
            ENGINE_CONN.execute("""
                INSERT INTO users_new (id, username, password_hash, bgg_id, created_at)
                SELECT id, username, password_hash, 
                       CASE WHEN bgg_id IS NOT NULL THEN CAST(bgg_id AS TEXT) ELSE NULL END,
                       created_at
                FROM users
            """)
            # Drop old table and rename new one
            ENGINE_CONN.execute("DROP TABLE users")
            ENGINE_CONN.execute("ALTER TABLE users_new RENAME TO users")
            ENGINE_CONN.commit()
            logger.info("Migration complete")
    except sqlite3.Error as e:
        logger.warning(f"Migration check failed (may already be migrated): {e}")
    
    # Add is_admin column if it doesn't exist
    try:
        cur = ENGINE_CONN.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cur.fetchall()}
        if 'is_admin' not in columns:
            logger.info("Adding is_admin column to users table")
            ENGINE_CONN.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            ENGINE_CONN.commit()
    except sqlite3.Error as e:
        logger.warning(f"Error adding is_admin column (may already exist): {e}")
    
    # Create admin user if it doesn't exist
    try:
        from backend.auth_utils import hash_password
        cur = ENGINE_CONN.execute("SELECT id FROM users WHERE username = ?", ("admin",))
        admin_user = cur.fetchone()
        if not admin_user:
            logger.info("Creating admin user")
            admin_password_hash = hash_password("admin")
            ENGINE_CONN.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                ("admin", admin_password_hash, 1)
            )
            ENGINE_CONN.commit()
            logger.info("Admin user created: username=admin, password=admin")
        else:
            # Ensure existing admin user has is_admin=1
            ENGINE_CONN.execute(
                "UPDATE users SET is_admin = 1 WHERE username = ?",
                ("admin",)
            )
            ENGINE_CONN.commit()
    except sqlite3.Error as e:
        logger.warning(f"Error creating/updating admin user: {e}")

    index = faiss.read_index(index_path)
    id_map = load_id_map(os.path.join(BASE_DIR, "gen", "game_ids.json"))
    ENGINE = SimilarityEngine(ENGINE_CONN, index, id_map)
    logger.info(f"SimilarityEngine initialized with {len(id_map)} games")


@app.on_event("shutdown")
def on_shutdown() -> None:
    global ENGINE_CONN
    if ENGINE_CONN is not None:
        ENGINE_CONN.close()
        ENGINE_CONN = None


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


@app.post("/auth/register")
def register(req: RegisterRequest):
    """Register a new user."""
    # Check if username exists
    cur = ENGINE_CONN.execute("SELECT id FROM users WHERE username = ?", (req.username,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Sanitize BGG ID
    bgg_id = req.bgg_id
    if bgg_id:
        if isinstance(bgg_id, str):
            bgg_id = bgg_id.strip() or None
        elif isinstance(bgg_id, int):
            bgg_id = str(bgg_id).strip() or None
    
    # Create user
    password_hash = hash_password(req.password)
    cur = ENGINE_CONN.execute(
        "INSERT INTO users (username, password_hash, bgg_id) VALUES (?, ?, ?)",
        (req.username, password_hash, bgg_id)
    )
    ENGINE_CONN.commit()
    user_id = cur.lastrowid
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user_id)})
    
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}


@app.post("/auth/login")
def login(req: LoginRequest):
    """Login and get access token."""
    cur = ENGINE_CONN.execute(
        "SELECT id, password_hash, bgg_id FROM users WHERE username = ?",
        (req.username,)
    )
    user = cur.fetchone()
    if not user or not verify_password(req.password, user[1]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": str(user[0])})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user[0]}


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
        cur = ENGINE_CONN.execute("SELECT is_admin FROM users WHERE id = ?", (current_user["id"],))
        row = cur.fetchone()
        current_user["is_admin"] = bool(row[0] if row else 0)
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        bgg_id=bgg_id,
        is_admin=current_user.get("is_admin", False)
    )


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
    ENGINE_CONN.execute(
        "UPDATE users SET bgg_id = ? WHERE id = ?",
        (bgg_id, current_user["id"])
    )
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
        # Ensure personal_rating column exists
        try:
            cur = ENGINE_CONN.execute("PRAGMA table_info(user_collections)")
            columns = [row[1] for row in cur.fetchall()]
            if "personal_rating" not in columns:
                ENGINE_CONN.execute("ALTER TABLE user_collections ADD COLUMN personal_rating REAL")
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
            cur = ENGINE_CONN.execute("SELECT id FROM games WHERE id = ?", (game_id,))
            if not cur.fetchone():
                logger.debug(f"Game {game_id} not found in local DB, skipping")
                skipped_count += 1
                continue
            
            # Check if already in collection
            cur = ENGINE_CONN.execute(
                "SELECT personal_rating FROM user_collections WHERE user_id = ? AND game_id = ?",
                (current_user["id"], game_id)
            )
            existing = cur.fetchone()
            
            if existing:
                # Update with new rating if provided
                if personal_rating is not None:
                    try:
                        ENGINE_CONN.execute(
                            "UPDATE user_collections SET personal_rating = ? WHERE user_id = ? AND game_id = ?",
                            (personal_rating, current_user["id"], game_id)
                        )
                        updated_count += 1
                    except sqlite3.Error as e:
                        logger.warning(f"Error updating game {game_id} rating: {e}")
            else:
                # Add to collection with rating
                try:
                    ENGINE_CONN.execute(
                        "INSERT INTO user_collections (user_id, game_id, personal_rating) VALUES (?, ?, ?)",
                        (current_user["id"], game_id, personal_rating)
                    )
                    added_count += 1
                except sqlite3.Error as e:
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
    """Search games by name with lookahead. Cached for performance."""
    # Input validation and sanitization
    if not q:
        return []
    q = q.strip()
    if len(q) < 2:
        return []
    
    # Sanitize to prevent SQL injection (though parameterized queries are safe)
    q = q.replace("%", "").replace("_", "")[:100]  # Limit length
    
    # Check cache
    cache_key = f"game_search:{q}:{limit}"
    cached_result = get_cached(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        # Split query into words for better matching
        # "Escape Curse" should match "Escape: The Curse of the Temple"
        query_words = q.split()
        
        # Build SQL with multiple LIKE conditions for each word
        # This allows partial word matching across the game name
        if len(query_words) == 1:
            # Single word: simple LIKE match
            sql = "SELECT id, name, year_published, thumbnail FROM games WHERE name LIKE ? ORDER BY name LIMIT ?"
            params = (f"%{query_words[0]}%", limit)
        else:
            # Multiple words: each word must appear somewhere in the name
            # Use LOWER for case-insensitive matching
            conditions = " AND ".join(["LOWER(name) LIKE LOWER(?)" for _ in query_words])
            sql = f"SELECT id, name, year_published, thumbnail FROM games WHERE {conditions} ORDER BY name LIMIT ?"
            params = tuple([f"%{word}%" for word in query_words] + [limit])
        
        cur = ENGINE_CONN.execute(sql, params)
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "name": row[1],
                "year_published": row[2],
                "thumbnail": row[3]
            })
        
        # If we got fewer results than limit, try a more lenient search
        # Match games where ANY word appears (OR instead of AND)
        if len(results) < limit and len(query_words) > 1:
            conditions = " OR ".join(["LOWER(name) LIKE LOWER(?)" for _ in query_words])
            sql = f"SELECT id, name, year_published, thumbnail FROM games WHERE {conditions} ORDER BY name LIMIT ?"
            params = tuple([f"%{word}%" for word in query_words] + [limit * 2])  # Get more for deduplication
            cur = ENGINE_CONN.execute(sql, params)
            additional_results = []
            seen_ids = {r["id"] for r in results}
            for row in cur.fetchall():
                if row[0] not in seen_ids:
                    additional_results.append({
                        "id": row[0],
                        "name": row[1],
                        "year_published": row[2],
                        "thumbnail": row[3]
                    })
                    seen_ids.add(row[0])
                    if len(results) + len(additional_results) >= limit:
                        break
            results.extend(additional_results)
            results = results[:limit]
        
        # Cache results
        set_cached(cache_key, results)
        logger.debug(f"Game search: '{q}' returned {len(results)} results")
        return results
    except sqlite3.Error as e:
        logger.error(f"Database error in game search: {e}", exc_info=True)
        return []


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
    
    # Check if personal_rating column exists, if not use NULL
    try:
        cur = ENGINE_CONN.execute("PRAGMA table_info(user_collections)")
        columns = [row[1] for row in cur.fetchall()]
        has_personal_rating = "personal_rating" in columns
    except:
        has_personal_rating = False
    
    personal_rating_col = "uc.personal_rating" if has_personal_rating else "NULL as personal_rating"
    
    cur = ENGINE_CONN.execute(
        f"""SELECT uc.game_id, g.name, g.year_published, g.thumbnail, uc.added_at,
                g.average_rating, {personal_rating_col}
           FROM user_collections uc
           JOIN games g ON uc.game_id = g.id
           WHERE uc.user_id = ?
           ORDER BY {order_by}""",
        (current_user["id"],)
    )
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
    cur = ENGINE_CONN.execute("SELECT id FROM games WHERE id = ?", (game_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Add to collection (ignore if already exists)
    ENGINE_CONN.execute(
        "INSERT OR IGNORE INTO user_collections (user_id, game_id) VALUES (?, ?)",
        (current_user["id"], game_id)
    )
    ENGINE_CONN.commit()
    logger.info(f"Added game {game_id} to collection for user {current_user['id']}")
    return {"success": True, "game_id": game_id}


@app.delete("/profile/collection/{game_id}")
def remove_from_collection(game_id: int, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Remove a game from user's collection."""
    cur = ENGINE_CONN.execute(
        "DELETE FROM user_collections WHERE user_id = ? AND game_id = ?",
        (current_user["id"], game_id)
    )
    ENGINE_CONN.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Game not in collection")
    return {"success": True}


@app.get("/chat/history")
def get_chat_history(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get list of chat threads for the user."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    cur = ENGINE_CONN.execute(
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
    cur = ENGINE_CONN.execute(
        "SELECT id FROM chat_threads WHERE id = ? AND user_id = ?",
        (thread_id, current_user["id"])
    )
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Get messages
    cur = ENGINE_CONN.execute(
        "SELECT id, role, message, metadata, created_at FROM chat_messages WHERE thread_id = ? ORDER BY created_at ASC",
        (thread_id,)
    )
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

    if intent == "recommend_similar":
        base_game_id = query_spec["base_game_id"]
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
        
        logger.debug(f"Search params: include_features={include_features}, exclude_features={exclude_features}, constraints={constraints}")
        
        try:
            # When searching in collection, we need to find more candidates since filtering is strict
            # The search_similar function already finds 2n matches and reorders, so this should work
            results = ENGINE.search_similar(
                game_id=base_game_id,
                top_k=top_k,
                include_self=False,
                constraints=constraints,
                allowed_ids=allowed_ids,
                explain=True,
                include_features=include_features,
                exclude_features=exclude_features,
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
                        )
                        results = results[:top_k] if results else []
                        logger.debug(f"Found {len(results)} results without constraints/features")
                    except Exception as search_err:
                        logger.error(f"Error in unconstrained search: {search_err}", exc_info=True)
                
                # If still no results, try embedding-only (no explain mode)
                if not results:
                    logger.debug(f"Retrying with embedding-only (no explain, no constraints, no features)")
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
            cur = ENGINE_CONN.execute("SELECT name FROM games WHERE id IN (?, ?)", (a, b))
            game_names = {row[0]: row[0] for row in cur.fetchall()}
            cur = ENGINE_CONN.execute("SELECT id, name FROM games WHERE id IN (?, ?)", (a, b))
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

    # Save to chat history (only if authenticated)
    thread_id = req.thread_id
    if current_user:
        if not thread_id:
            # Create new thread
            cur = ENGINE_CONN.execute(
                "INSERT INTO chat_threads (user_id, title) VALUES (?, ?)",
                (current_user["id"], req.message[:50])  # Use first 50 chars as title
            )
            ENGINE_CONN.commit()
            thread_id = cur.lastrowid
            logger.debug(f"Created new chat thread {thread_id} for user {current_user['id']}")
        
        # Save user message
        ENGINE_CONN.execute(
            "INSERT INTO chat_messages (thread_id, role, message) VALUES (?, ?, ?)",
            (thread_id, "user", req.message)
        )
        
        # Save assistant message
        metadata = {
            "results": results,
            "query_spec": query_spec
        }
        ENGINE_CONN.execute(
            "INSERT INTO chat_messages (thread_id, role, message, metadata) VALUES (?, ?, ?, ?)",
            (thread_id, "assistant", reply_text, json.dumps(metadata))
        )
        
        # Update thread updated_at
        ENGINE_CONN.execute(
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
        thread_id=thread_id,
    )


@app.post("/image/generate")
async def generate_from_image(
    file: UploadFile = File(...),
    api_type: str = "stable_diffusion",
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Upload image, analyze it, generate prompt, and create new image."""
    logger.info(f"Image upload request from user: {current_user['id'] if current_user else 'anonymous'}")
    
    # Input validation
    if file.content_type and not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Limit file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    try:
        # Read image data
        image_data = await file.read()
        if len(image_data) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
        
        logger.debug(f"Received image: {file.filename}, size: {len(image_data)} bytes")
        
        # Validate API type
        if api_type not in ["stable_diffusion", "dalle"]:
            api_type = "stable_diffusion"
        
        # Analyze image
        analysis = analyze_image(image_data)
        
        # Generate prompt
        prompt = generate_prompt_from_analysis(analysis)
        
        # Generate new image
        generated_image = generate_image(prompt, api_type=api_type)
        
        # Return as base64 for frontend
        import base64
        image_base64 = base64.b64encode(generated_image).decode('utf-8')
        
        logger.info("Image generation complete")
        return {
            "success": True,
            "image": f"data:image/png;base64,{image_base64}",
            "prompt": prompt,
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")


@app.get("/games/{game_id}/features")
def get_game_features_endpoint(game_id: int, current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)):
    """Get all features for a game, including original and modifications. Admin only."""
    try:
        # Get original features
        features = get_game_features(ENGINE_CONN, game_id)
        
        # Get feature modifications
        cur = ENGINE_CONN.execute(
            """SELECT feature_type, feature_id, action 
               FROM feature_mods 
               WHERE game_id = ? 
               ORDER BY created_at DESC""",
            (game_id,)
        )
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
            cur = ENGINE_CONN.execute(f"SELECT id, name FROM {table_name} ORDER BY name")
            available_features[feature_type] = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
        
        # Apply modifications
        for mod in mods:
            feature_type = mod[0]
            feature_id = mod[1]
            action = mod[2]
            
            # Find feature name
            table_name = feature_type if feature_type != "families" else "families"
            cur = ENGINE_CONN.execute(f"SELECT name FROM {table_name} WHERE id = ?", (feature_id,))
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
        cur = ENGINE_CONN.execute("SELECT id FROM games WHERE id = ?", (game_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Verify feature exists
        table_name = feature_type if feature_type != "families" else "families"
        cur = ENGINE_CONN.execute(f"SELECT id FROM {table_name} WHERE id = ?", (feature_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Check if modification already exists
        cur = ENGINE_CONN.execute(
            """SELECT id FROM feature_mods 
               WHERE game_id = ? AND feature_type = ? AND feature_id = ? AND action = ?""",
            (game_id, feature_type, feature_id, action)
        )
        existing = cur.fetchone()
        
        if existing:
            # Modification already exists, return success
            return {"success": True, "message": "Modification already exists"}
        
        # Remove opposite action if it exists
        opposite_action = "remove" if action == "add" else "add"
        ENGINE_CONN.execute(
            """DELETE FROM feature_mods 
               WHERE game_id = ? AND feature_type = ? AND feature_id = ? AND action = ?""",
            (game_id, feature_type, feature_id, opposite_action)
        )
        
        # Add new modification
        ENGINE_CONN.execute(
            """INSERT INTO feature_mods (game_id, feature_type, feature_id, action)
               VALUES (?, ?, ?, ?)""",
            (game_id, feature_type, feature_id, action)
        )
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
        cur = ENGINE_CONN.execute(
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
        cur = ENGINE_CONN.execute("SELECT name FROM games WHERE id = ?", (game_id,))
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
        cur = ENGINE_CONN.execute(
            """SELECT id, question_text, question_type 
               FROM feedback_questions 
               WHERE is_active = 1 
               ORDER BY RANDOM() 
               LIMIT 1"""
        )
        row = cur.fetchone()
        
        if not row:
            return None
        
        question_id = row[0]
        
        # Get options for this question with their IDs
        cur = ENGINE_CONN.execute(
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
        # Try to find existing question
        cur = ENGINE_CONN.execute(
            """SELECT id FROM feedback_questions 
               WHERE question_text = 'Were these results helpful?' 
               LIMIT 1"""
        )
        row = cur.fetchone()
        
        if row:
            question_id = row[0]
        else:
            # Create the question if it doesn't exist
            cur = ENGINE_CONN.execute(
                """INSERT INTO feedback_questions (question_text, question_type, is_active)
                   VALUES (?, ?, ?)""",
                ("Were these results helpful?", "single_select", 1)
            )
            question_id = cur.lastrowid
            
            # Create Yes and No options
            ENGINE_CONN.execute(
                """INSERT INTO feedback_question_options (question_id, option_text, display_order)
                   VALUES (?, ?, ?)""",
                (question_id, "Yes", 0)
            )
            ENGINE_CONN.execute(
                """INSERT INTO feedback_question_options (question_id, option_text, display_order)
                   VALUES (?, ?, ?)""",
                (question_id, "No", 1)
            )
            ENGINE_CONN.commit()
        
        # Get options with their IDs
        cur = ENGINE_CONN.execute(
            """SELECT id, option_text FROM feedback_question_options 
               WHERE question_id = ? 
               ORDER BY display_order, id""",
            (question_id,)
        )
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
            cur = ENGINE_CONN.execute(
                "SELECT id, question_type FROM feedback_questions WHERE id = ? AND is_active = 1",
                (question_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Question not found")
            
            question_type = row[1]
            
            # For single_select, verify option_id exists and belongs to this question
            if question_type == "single_select":
                if option_id is None:
                    raise HTTPException(status_code=400, detail="option_id required for single_select questions")
                cur = ENGINE_CONN.execute(
                    "SELECT id FROM feedback_question_options WHERE id = ? AND question_id = ?",
                    (option_id, question_id)
                )
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
                        cur = ENGINE_CONN.execute(
                            "SELECT id FROM feedback_question_options WHERE id = ? AND question_id = ?",
                            (opt_id, question_id)
                        )
                        if not cur.fetchone():
                            raise HTTPException(status_code=404, detail=f"Option {opt_id} not found or doesn't belong to question")
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON in response for multi_select question")
        
        # For multi_select, create one response record per selected option
        if question_type == "multi_select" and response:
            try:
                option_ids = json.loads(response)
                for opt_id in option_ids:
                    ENGINE_CONN.execute(
                        """INSERT INTO user_feedback_responses 
                           (user_id, question_id, option_id, response, context, thread_id)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            int(current_user["id"]), 
                            question_id, 
                            opt_id,  # Each option gets its own record
                            None,  # response field is None for multi_select (option_id is used)
                            context if context is not None else None, 
                            thread_id if thread_id is not None else None
                        )
                    )
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in response")
        else:
            # For single_select or text, create a single response record
            # Ensure all fields are properly set
            logger.debug(f"Inserting feedback: user_id={int(current_user['id'])}, question_id={question_id}, option_id={option_id}, response={response}, context={context}, thread_id={thread_id}")
            ENGINE_CONN.execute(
                """INSERT INTO user_feedback_responses 
                   (user_id, question_id, option_id, response, context, thread_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    int(current_user["id"]),  # Ensure user_id is int
                    question_id,
                    option_id,
                    response,
                    context,
                    thread_id
                )
            )
        
        ENGINE_CONN.commit()
        
        # Verify the record was inserted
        cur = ENGINE_CONN.execute(
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
        
        cur = ENGINE_CONN.execute(count_sql, count_params)
        total = cur.fetchone()[0]
        
        cur = ENGINE_CONN.execute(sql, params)
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
        cur = ENGINE_CONN.execute(
            """SELECT id, question_text, question_type, is_active, created_at 
               FROM feedback_questions 
               ORDER BY created_at DESC"""
        )
        questions = []
        for row in cur.fetchall():
            question_id = row[0]
            # Get options for this question
            cur_opts = ENGINE_CONN.execute(
                """SELECT id, option_text, display_order 
                   FROM feedback_question_options 
                   WHERE question_id = ? 
                   ORDER BY display_order, id""",
                (question_id,)
            )
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
        cur = ENGINE_CONN.execute(
            """INSERT INTO feedback_questions (question_text, question_type, is_active)
               VALUES (?, ?, ?)""",
            (req.question_text, req.question_type, 1 if req.is_active else 0)
        )
        question_id = cur.lastrowid
        
        # Insert options if provided (for single_select or multi_select)
        if req.options and req.question_type in ["single_select", "multi_select"]:
            for idx, option_text in enumerate(req.options):
                if option_text.strip():  # Only insert non-empty options
                    ENGINE_CONN.execute(
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
        cur = ENGINE_CONN.execute("SELECT id FROM feedback_questions WHERE id = ?", (question_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Question not found")
        
        if req.question_type not in ["text", "single_select", "multi_select"]:
            raise HTTPException(status_code=400, detail="Invalid question type")
        
        # Update question fields
        ENGINE_CONN.execute(
            """UPDATE feedback_questions 
               SET question_text = ?, question_type = ?, is_active = ?
               WHERE id = ?""",
            (req.question_text, req.question_type, 1 if req.is_active else 0, question_id)
        )
        
        # Update options
        # Delete existing options
        ENGINE_CONN.execute(
            "DELETE FROM feedback_question_options WHERE question_id = ?",
            (question_id,)
        )
        # Insert new options if provided (for single_select or multi_select)
        if req.options and req.question_type in ["single_select", "multi_select"]:
            for idx, option_text in enumerate(req.options):
                if option_text.strip():  # Only insert non-empty options
                    ENGINE_CONN.execute(
                        """INSERT INTO feedback_question_options (question_id, option_text, display_order)
                           VALUES (?, ?, ?)""",
                        (question_id, option_text, idx)
                    )
        
        ENGINE_CONN.commit()
        return {"success": True, "message": "Question updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feedback question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update question: {str(e)}")


@app.delete("/admin/feedback/questions/{question_id}")
def delete_feedback_question(
    question_id: int,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_admin_user)
):
    """Delete a feedback question (and its options via CASCADE)."""
    try:
        cur = ENGINE_CONN.execute("SELECT id FROM feedback_questions WHERE id = ?", (question_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Question not found")
        
        ENGINE_CONN.execute("DELETE FROM feedback_questions WHERE id = ?", (question_id,))
        ENGINE_CONN.commit()
        return {"success": True, "message": "Question deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting feedback question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete question: {str(e)}")

