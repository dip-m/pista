# backend/app/chat_nlu.py

import json
import os
import re
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
NAME_MAP_PATH = os.path.join(BASE_DIR, "..", "name_id_map.json")

with open(NAME_MAP_PATH, "r", encoding="utf-8") as f:
    NAME_TO_ID: Dict[str, Any] = json.load(f)


def normalize(text: str) -> str:
    """
    Normalize free text / names:
    - lowercase
    - keep letters, digits, underscore, space, colon
    - collapse whitespace
    """
    text = text.lower()
    text = re.sub(r"[^\w\s:]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# -------------------------------------------------------------------
# Build a more robust name index for matching
# -------------------------------------------------------------------

NAME_INDEX: List[Dict[str, Any]] = []

for name_key, gid in NAME_TO_ID.items():
    norm = normalize(name_key)
    tokens = norm.split()
    if not tokens:
        continue

    NAME_INDEX.append(
        {
            "name": norm,          # normalized full name
            "tokens": tokens,      # token list
            "token_len": len(tokens),
            "char_len": len(norm),
            "id": gid,
        }
    )

# Longer, more specific names first
NAME_INDEX.sort(
    key=lambda x: (x["token_len"], x["char_len"]),
    reverse=True,
)


# -------------------------------------------------------------------
# Candidate resolution: multi-game, scored, collection-aware
# -------------------------------------------------------------------

def resolve_game_candidates(
    text: str,
    user_collection: Optional[List[Any]] = None,
    max_candidates: int = 3,
) -> List[Dict[str, Any]]:
    """
    Find up to `max_candidates` games mentioned in `text`.

    Returns list of:
      {
        "game_id": ...,
        "name_key": ...,
        "match_type": "phrase" | "token",
        "score": float,
        "in_collection": bool,
      }

    Scoring:
      - phrase match (with word boundaries): base 1.0
      - token-set match (all tokens present): base 0.8
      - +0.1 if game is in user's collection
    """
    text_norm = normalize(text)
    words = text_norm.split()
    word_set = set(words)
    user_collection_set = set(user_collection or [])

    candidates: List[Dict[str, Any]] = []

    # 1️⃣ Phrase matches with word boundaries
    for entry in NAME_INDEX:
        pattern = rf"\b{re.escape(entry['name'])}\b"
        if re.search(pattern, text_norm):
            gid = entry["id"]
            in_col = gid in user_collection_set
            score = 1.0 + (0.1 if in_col else 0.0)
            candidates.append(
                {
                    "game_id": gid,
                    "name_key": entry["name"],
                    "match_type": "phrase",
                    "score": score,
                    "in_collection": in_col,
                }
            )

    # 2️⃣ Token-based matches (only if phrase match didn't already cover it)
    for entry in NAME_INDEX:
        if any(c["game_id"] == entry["id"] for c in candidates):
            continue  # already have phrase entry

        tokens = entry["tokens"]
        if all(tok in word_set for tok in tokens):
            gid = entry["id"]
            in_col = gid in user_collection_set
            score = 0.8 + (0.1 if in_col else 0.0)
            candidates.append(
                {
                    "game_id": gid,
                    "name_key": entry["name"],
                    "match_type": "token",
                    "score": score,
                    "in_collection": in_col,
                }
            )

    # 3️⃣ Sort by score descending, then by name length
    candidates.sort(
        key=lambda c: (c["score"], len(c["name_key"])),
        reverse=True,
    )

    # 4️⃣ De-duplicate by game_id, keep best-scoring variant
    deduped: Dict[Any, Dict[str, Any]] = {}
    for c in candidates:
        gid = c["game_id"]
        if gid not in deduped or c["score"] > deduped[gid]["score"]:
            deduped[gid] = c

    final = list(deduped.values())
    final.sort(key=lambda c: c["score"], reverse=True)

    return final[:max_candidates]


# -------------------------------------------------------------------
# interpret_message using multi-game + scores + collection
# -------------------------------------------------------------------

def interpret_message(
    user_id: str, text: str, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Rules-based interpreter → QuerySpec.
    
    If context contains 'selected_game_id', it will be used as base_game_id,
    bypassing NLU game resolution.
    """
    """
    Rules-based interpreter → QuerySpec.

    QuerySpec shapes:

    1) recommend_similar
        {
          "intent": "recommend_similar",
          "base_game_id": ...,
          "scope": "user_collection" | "global",
          "top_k": 5,
          "constraints": {...},
          "nlu_debug": {...}
        }

    2) compare_pair
        {
          "intent": "compare_pair",
          "game_a_id": ...,
          "game_b_id": ...,
          ...
        }
    """
    text_l = text.lower()
    ctx = context or {}
    user_collection_ids: List[Any] = ctx.get("user_collection_ids") or []

    query_spec: Dict[str, Any] = {
        "intent": "recommend_similar",
        "scope": "global",
        "top_k": 5,
        "constraints": {},
        "nlu_debug": {},
    }

    # multi-game extraction with scores
    candidates = resolve_game_candidates(text, user_collection_ids, max_candidates=3)
    query_spec["nlu_debug"]["candidates"] = candidates

    last_game_id = ctx.get("last_game_id")
    selected_game_id = ctx.get("selected_game_id")  # From search selection
    base_game_id: Optional[Any] = None

    # Priority: selected_game_id > candidates > last_game_id > fallback
    if selected_game_id:
        base_game_id = selected_game_id
    elif candidates:
        base_game_id = candidates[0]["game_id"]
    else:
        base_game_id = last_game_id or 224517  # fallback: Brass: Birmingham

    # If at least two games & language suggests comparison → compare_pair
    if len(candidates) >= 2 and ("compare" in text_l or "do i need" in text_l):
        query_spec["intent"] = "compare_pair"
        query_spec["game_a_id"] = candidates[0]["game_id"]
        query_spec["game_b_id"] = candidates[1]["game_id"]
        return query_spec

    # Set base_game_id in query_spec
    query_spec["base_game_id"] = base_game_id

    # scope - check context first, then text
    # Context useCollection takes priority
    if context and context.get("useCollection"):
        query_spec["scope"] = "user_collection"
        logger.debug(f"Setting scope to user_collection from context.useCollection")
    elif "my collection" in text_l or "in my collection" in text_l:
        query_spec["scope"] = "user_collection"
        logger.debug(f"Setting scope to user_collection from text")

    cons: Dict[str, Any] = {}

    # constraints
    if re.search(r"same\s+(author|designer)", text_l):
        cons.setdefault("designers", {})["min_overlap"] = 1

    if re.search(r"same\s+(mechanics?|mechanisms?)", text_l):
        cons.setdefault("mechanics", {})["jaccard_min"] = 0.5

    if re.search(r"same\s+(theme|category|categories)", text_l):
        cons.setdefault("categories", {})["jaccard_min"] = 0.5

    # Handle "different" / "dissimilar" logic
    if "different" in text_l or "dissimilar" in text_l or "not" in text_l:
        if "mechanic" in text_l or "mechanism" in text_l:
            cons.setdefault("mechanics", {})["jaccard_max"] = 0.2
            # Also add to exclude_features if very strict
            if "completely different" in text_l or "no" in text_l:
                query_spec.setdefault("exclude_features", []).append("mechanics")
        if "theme" in text_l or "category" in text_l or "categories" in text_l:
            cons.setdefault("categories", {})["jaccard_max"] = 0.2
            if "completely different" in text_l or "no" in text_l:
                query_spec.setdefault("exclude_features", []).append("categories")
                # Also exclude families when different theme is requested
                if "exclude_features" not in query_spec:
                    query_spec["exclude_features"] = []
                if "families" not in query_spec["exclude_features"]:
                    query_spec["exclude_features"].append("families")
        if "designer" in text_l or "author" in text_l:
            cons.setdefault("designers", {})["max_overlap"] = 0
            if "completely different" in text_l:
                query_spec.setdefault("exclude_features", []).append("designers")

    query_spec["constraints"] = cons
    return query_spec
