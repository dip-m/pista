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
        cur = ENGINE_CONN.execute("SELECT id, username, bgg_id FROM users WHERE id = ?", (int(user_id),))
        user = cur.fetchone()
        if user is None:
            return None
        # #region agent log
        import json, os
        log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        bgg_id_val = user[2] if len(user) > 2 else None
        logger.debug(f"[DEBUG] get_current_user - user_id: {user[0]}, bgg_id: {bgg_id_val}, bgg_id_type: {type(bgg_id_val).__name__}")
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"C","location":"main.py:135","message":"get_current_user result","data":{"user_id":user[0],"bgg_id":bgg_id_val,"bgg_id_type":type(bgg_id_val).__name__},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion
        return {"id": user[0], "username": user[1], "bgg_id": user[2] if len(user) > 2 else None}
    except Exception as e:
        logger.debug(f"Error getting current user: {e}", exc_info=True)
        return None


def get_current_user_required(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token. Raises exception if not authenticated."""
    user = get_current_user(credentials)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
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
    # #region agent log
    import json, os
    log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"main.py:186","message":"Register request received","data":{"username":req.username,"bgg_id":req.bgg_id,"bgg_id_type":type(req.bgg_id).__name__},"timestamp":int(__import__('time').time()*1000)})+'\n')
    # #endregion
    
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
    
    # #region agent log
    import json, os
    log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"main.py:200","message":"BGG ID after sanitization","data":{"bgg_id":bgg_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
    # #endregion
    
    # Create user
    password_hash = hash_password(req.password)
    cur = ENGINE_CONN.execute(
        "INSERT INTO users (username, password_hash, bgg_id) VALUES (?, ?, ?)",
        (req.username, password_hash, bgg_id)
    )
    ENGINE_CONN.commit()
    user_id = cur.lastrowid
    
    # #region agent log
    import json, os
    log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"main.py:212","message":"User registered","data":{"user_id":user_id,"bgg_id":bgg_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
    # #endregion
    
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
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        bgg_id=bgg_id
    )


@app.put("/profile/bgg-id")
def update_bgg_id(req: BggIdUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Update user's BGG ID (can be text/username or numeric ID)."""
    # #region agent log
    import json, os
    log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:287","message":"BGG ID update request received","data":{"user_id":current_user["id"],"bgg_id_received":req.bgg_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
    # #endregion
    
    # Validate and sanitize input
    bgg_id = req.bgg_id
    if bgg_id:
        bgg_id = bgg_id.strip()
        if not bgg_id:
            bgg_id = None
    else:
        bgg_id = None
    
    # #region agent log
    import json, os
    log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:302","message":"BGG ID after sanitization","data":{"bgg_id":bgg_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
    # #endregion
    
    logger.info(f"Updating BGG ID for user {current_user['id']} to {bgg_id}")
    ENGINE_CONN.execute(
        "UPDATE users SET bgg_id = ? WHERE id = ?",
        (bgg_id, current_user["id"])
    )
    ENGINE_CONN.commit()
    
    # #region agent log
    import json, os
    log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:315","message":"BGG ID updated in database","data":{"user_id":current_user["id"],"bgg_id":bgg_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
    # #endregion
    
    logger.info(f"BGG ID updated successfully for user {current_user['id']}")
    return {"success": True, "bgg_id": bgg_id}


@app.post("/profile/collection/import-bgg")
def import_bgg_collection(current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Import collection from BGG."""
    # #region agent log
    import json, os
    log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger.info(f"[DEBUG] Import BGG collection request - user_id: {current_user['id']}, bgg_id: {current_user.get('bgg_id')}")
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"C","location":"main.py:325","message":"Import BGG collection request","data":{"user_id":current_user["id"],"bgg_id":current_user.get("bgg_id"),"bgg_id_type":type(current_user.get("bgg_id")).__name__},"timestamp":int(__import__('time').time()*1000)})+'\n')
    # #endregion
    
    bgg_id_value = current_user.get("bgg_id")
    if not bgg_id_value:
        # #region agent log
        logger.warning(f"[DEBUG] BGG ID missing for user {current_user['id']}")
        import json, os
        log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"C","location":"main.py:333","message":"BGG ID missing error","data":{"user_id":current_user["id"],"bgg_id":bgg_id_value},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion
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
        cur = ENGINE_CONN.execute(
            "SELECT id, name, year_published, thumbnail FROM games WHERE name LIKE ? ORDER BY name LIMIT ?",
            (f"%{q}%", limit)
        )
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "name": row[1],
                "year_published": row[2],
                "thumbnail": row[3]
            })
        
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
        scope = query_spec.get("scope", "global")
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
        except Exception as e:
            logger.error(f"Error searching similar games: {e}", exc_info=True)
            results = []

        if results:
            excluded_text = ""
            if exclude_features:
                excluded_text = f" (excluding: {', '.join(exclude_features)})"
            reply_text = (
                f"Here are some games that feel close to your base game "
                f"(intent: {intent}, scope: {scope}){excluded_text}:"
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


@app.get("/marketplace/search")
def search_marketplace(
    game_id: int,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Search marketplace listings for a game from multiple sources.
    Returns aggregated results from Amazon, eBay, GeekMarket, and Wallapop.
    """
    try:
        # Get game name for search
        cur = ENGINE_CONN.execute("SELECT name FROM games WHERE id = ?", (game_id,))
        game_row = cur.fetchone()
        if not game_row:
            raise HTTPException(status_code=404, detail="Game not found")
        
        game_name = game_row[0]
        
        # TODO: Integrate with real marketplace APIs
        # For now, return mock data structure
        # In production, this would:
        # 1. Search Amazon Product Advertising API
        # 2. Search eBay Finding API
        # 3. Search BoardGameGeek GeekMarket
        # 4. Search Wallapop API
        
        listings = []
        
        # Mock Amazon listing
        listings.append({
            "platform": "Amazon",
            "price": 29.99,
            "currency": "$",
            "shipping_included": True,
            "condition": "New",
            "location": "USA",
            "seller_rating": 4.8,
            "seller_reviews": 1250,
            "url": f"https://www.amazon.com/s?k={game_name.replace(' ', '+')}",
        })
        
        # Mock eBay listing
        listings.append({
            "platform": "eBay",
            "price": 24.99,
            "currency": "$",
            "shipping_included": False,
            "condition": "Used",
            "location": "UK",
            "seller_rating": 4.6,
            "seller_reviews": 342,
            "url": f"https://www.ebay.com/sch/i.html?_nkw={game_name.replace(' ', '+')}",
        })
        
        # Mock GeekMarket listing
        listings.append({
            "platform": "GeekMarket",
            "price": 22.50,
            "currency": "$",
            "shipping_included": False,
            "condition": "Like New",
            "location": "USA",
            "seller_rating": 4.9,
            "seller_reviews": 89,
            "url": f"https://boardgamegeek.com/geekmarket/browse?query={game_name.replace(' ', '+')}",
        })
        
        # Mock Wallapop listing
        listings.append({
            "platform": "Wallapop",
            "price": 18.00,
            "currency": "€",
            "shipping_included": True,
            "condition": "Used",
            "location": "Spain",
            "seller_rating": 4.7,
            "seller_reviews": 156,
            "url": f"https://es.wallapop.com/search?keywords={game_name.replace(' ', '+')}",
        })
        
        return {
            "game_id": game_id,
            "game_name": game_name,
            "listings": listings,
            "total": len(listings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching marketplace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search marketplace: {str(e)}")

