# api/chat_service.py
# NOTE: This is a stub/example file. The actual chat implementation is in backend/main.py
import json
import faiss
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Set

from backend.similarity_engine import SimilarityEngine
from backend.chat_nlu import interpret_message
from backend.main import load_user_collection, compare_two_games
from .db import db_connection, ensure_schema


# Stub functions for reply rendering (actual implementation is in main.py)
def render_recommendation_reply(query_spec: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    """Render a recommendation reply from query spec and results."""
    return "Here are some similar games you might enjoy."


def render_comparison_reply(comparison: Dict[str, Any]) -> str:
    """Render a comparison reply from comparison results."""
    return "Here's a comparison of the two games."


app = FastAPI()


# You'd probably manage this via dependency injection / startup events.
def get_engine() -> SimilarityEngine:
    conn = db_connection("gen/pista_semantic.db").__enter__()  # pseudo
    ensure_schema(conn)
    index = faiss.read_index("gen/game_vectors.index")
    with open("gen/game_ids.json", "r", encoding="utf-8") as f:
        id_map = json.load(f)
    return SimilarityEngine(conn, index, id_map)


class ChatRequest(BaseModel):
    user_id: str
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply_text: str
    results: Optional[List[Dict[str, Any]]] = None
    query_spec: Optional[Dict[str, Any]] = None


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, engine: SimilarityEngine = Depends(get_engine)):
    # 1) NLU: use an LLM or rule-based parser to build QuerySpec
    query_spec = interpret_message(req.user_id, req.message, req.context)

    if query_spec["intent"] == "recommend_similar":
        user_collection_ids: Optional[Set[int]] = None
        if query_spec.get("scope") == "user_collection":
            user_collection_ids = load_user_collection(req.user_id)

        results = engine.search_similar(
            game_id=query_spec["base_game_id"],
            top_k=query_spec.get("top_k", 5),
            include_self=False,
            constraints=query_spec.get("constraints") or {},
            allowed_ids=user_collection_ids,
            explain=True,
        )
        reply = render_recommendation_reply(query_spec, results)

    elif query_spec["intent"] == "compare_pair":
        # Call your compare_games logic
        game_a_id = query_spec.get("game_a_id")
        game_b_id = query_spec.get("game_b_id")
        comparison = compare_two_games(engine, game_a_id, game_b_id)
        results = [comparison]
        reply = render_comparison_reply(comparison)

    else:
        reply = "I�m not sure what to do with that yet."
        results = None

    return ChatResponse(
        reply_text=reply,
        results=results,
        query_spec=query_spec,
    )
