# backend/app/chat_nlu.py

import json
import os
import re
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
NAME_MAP_PATH = os.path.join(BASE_DIR, "..", "name_id_map.json")


# Load name_id_map.json, or generate it from database if it doesn't exist
def load_name_id_map() -> Dict[str, Any]:
    """Load name_id_map.json, generating it from database if needed."""
    if os.path.exists(NAME_MAP_PATH):
        try:
            with open(NAME_MAP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load {NAME_MAP_PATH}: {e}. Will generate from database.")

    # File doesn't exist or failed to load - generate from database
    logger.info(f"{NAME_MAP_PATH} not found. Generating from database...")
    try:
        from update_utils.export_name_id_map import get_name_id_map
        from backend.db import get_connection, put_connection

        # Get database connection
        conn = get_connection()
        try:
            # Generate from database (works with both SQLite and PostgreSQL)
            name_id_map = get_name_id_map(conn)
            # Save it for future use
            try:
                os.makedirs(os.path.dirname(NAME_MAP_PATH), exist_ok=True)
                with open(NAME_MAP_PATH, "w", encoding="utf-8") as f:
                    json.dump(name_id_map, f, ensure_ascii=False, indent=2)
                logger.info(f"Generated and saved {NAME_MAP_PATH} with {len(name_id_map)} entries")
            except Exception as save_err:
                logger.warning(f"Could not save {NAME_MAP_PATH}: {save_err}. Using in-memory map.")
            return name_id_map
        finally:
            put_connection(conn)
    except Exception as e:
        logger.error(f"Failed to generate name_id_map from database: {e}", exc_info=True)
        # Return empty dict as fallback - game name resolution won't work, but app won't crash
        return {}


NAME_TO_ID: Dict[str, Any] = load_name_id_map()


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
            "name": norm,  # normalized full name
            "tokens": tokens,  # token list
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


def interpret_message(user_id: str, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
    text_l = text.lower().strip()
    ctx = context or {}
    user_collection_ids: List[Any] = ctx.get("user_collection_ids") or []

    # Detect theme/mechanics preference responses
    # Check if this is a response to the follow-up prompt
    theme_preference = None
    mechanics_preference = None
    # Check for exact match first (most specific)
    if text_l.strip() == "1" or text_l.strip() == "theme" or text_l.strip() == "the theme":
        theme_preference = "theme"
    elif text_l.strip() == "2" or text_l.strip() == "mechanics" or text_l.strip() == "the mechanics":
        mechanics_preference = "mechanics"
    # Then check for partial matches
    elif any(word in text_l for word in ["theme", "prefer theme", "theme preference"]):
        theme_preference = "theme"
    elif any(word in text_l for word in ["mechanics", "prefer mechanics", "mechanics preference"]):
        mechanics_preference = "mechanics"

    # Store in context for use in chat endpoint
    if theme_preference:
        ctx["theme_preference"] = theme_preference
    if mechanics_preference:
        ctx["mechanics_preference"] = mechanics_preference

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
    # But don't use fallback if we have features in context (allow feature-only search)
    # For theme/mechanics preference responses, always use last_game_id if available
    has_features_in_context = (
        (ctx.get("required_feature_values") and len(ctx.get("required_feature_values", {})) > 0)
        or (ctx.get("player_chips") and len(ctx.get("player_chips", [])) > 0)
        or (ctx.get("playtime_chips") and len(ctx.get("playtime_chips", [])) > 0)
    )

    # If this is a theme/mechanics preference response, prioritize last_game_id
    if (theme_preference or mechanics_preference) and last_game_id:
        base_game_id = last_game_id
    elif selected_game_id:
        base_game_id = selected_game_id
    elif candidates and not has_features_in_context:
        # Only use candidates if we don't have features in context
        # If features are present, prefer feature-only search over game candidates
        base_game_id = candidates[0]["game_id"]
    elif last_game_id and not has_features_in_context:
        # Only use last_game_id if we don't have features in context
        # If features are present, prefer feature-only search
        base_game_id = last_game_id
    elif not has_features_in_context:
        # Only use fallback if no features in context (allow feature-only search when features are present)
        base_game_id = 224517  # fallback: Brass: Birmingham
    else:
        base_game_id = None  # Allow feature-only search

    # Check for "Do I need X in my collection?" intent
    if "do i need" in text_l and len(candidates) >= 1:
        query_spec["intent"] = "collection_recommendation"
        query_spec["base_game_id"] = candidates[0]["game_id"]
        return query_spec

    # If at least two games & language suggests comparison → compare_pair
    if len(candidates) >= 2 and "compare" in text_l:
        query_spec["intent"] = "compare_pair"
        query_spec["game_a_id"] = candidates[0]["game_id"]
        query_spec["game_b_id"] = candidates[1]["game_id"]
        return query_spec

    # Set base_game_id in query_spec (may be None for feature-only search)
    query_spec["base_game_id"] = base_game_id

    # scope - check context first, then text
    # Context useCollection takes priority
    if context and context.get("useCollection"):
        query_spec["scope"] = "user_collection"
        logger.debug(f"Setting scope to user_collection from context.useCollection")
    elif "my collection" in text_l or "in my collection" in text_l:
        query_spec["scope"] = "user_collection"
        logger.debug(f"Setting scope to user_collection from text")

    # Pass through excluded_feature_values from context
    if context and context.get("excluded_feature_values"):
        query_spec["excluded_feature_values"] = context["excluded_feature_values"]
        logger.debug(f"Setting excluded_feature_values from context: {context['excluded_feature_values']}")

    # Pass through required_feature_values from context
    if context and context.get("required_feature_values"):
        query_spec["required_feature_values"] = context["required_feature_values"]
        logger.debug(f"Setting required_feature_values from context: {context['required_feature_values']}")

    # Pass through use_rarity_weighting from context if set
    if context and context.get("use_rarity_weighting") is not None:
        query_spec["use_rarity_weighting"] = context["use_rarity_weighting"]

    cons: Dict[str, Any] = {}

    # constraints
    if re.search(r"same\s+(author|designer)", text_l):
        cons.setdefault("designers", {})["min_overlap"] = 1

    if re.search(r"same\s+(mechanics?|mechanisms?)", text_l):
        cons.setdefault("mechanics", {})["jaccard_min"] = 0.5

    if re.search(r"same\s+(theme|category|categories)", text_l):
        cons.setdefault("categories", {})["jaccard_min"] = 0.5

    # Handle player count constraints from context chips (priority) or text
    player_chips = ctx.get("player_chips", [])
    if player_chips and len(player_chips) > 0:
        # Use the first player chip as the target player count
        player_count = player_chips[0] if isinstance(player_chips[0], int) else int(player_chips[0])
        cons.setdefault("players", {})["exact"] = player_count
        cons.setdefault("players", {})["use_recommended"] = True  # Use polls_json recommended players for similarity
    else:
        # Fall back to text parsing
        player_match = re.search(r"(\d+)\s*player", text_l)
        if player_match:
            player_count = int(player_match.group(1))
            cons.setdefault("players", {})["exact"] = player_count
            cons.setdefault("players", {})["use_recommended"] = True

        # Handle player range (e.g., "2-4 players", "2 to 4 players")
        player_range_match = re.search(r"(\d+)\s*[-to]\s*(\d+)\s*player", text_l)
        if player_range_match:
            min_players = int(player_range_match.group(1))
            max_players = int(player_range_match.group(2))
            cons.setdefault("players", {})["min_overlap"] = 1  # At least 1 player overlap

        # Handle "same player count" or "similar player count"
        if "same player" in text_l or "similar player" in text_l:
            cons.setdefault("players", {})["similar_best"] = True

    # Handle playtime constraints from context chips (priority) or text
    playtime_chips = ctx.get("playtime_chips", [])
    if playtime_chips and len(playtime_chips) > 0:
        # Use the first playtime chip as the target playtime (in minutes)
        playtime_minutes = playtime_chips[0] if isinstance(playtime_chips[0], int) else int(playtime_chips[0])
        cons.setdefault("playtime", {})["target"] = playtime_minutes
        cons.setdefault("playtime", {})["tolerance"] = 0.3  # 30% tolerance (e.g., 60 min ± 18 min)
    else:
        # Fall back to text parsing for playtime
        playtime_match = re.search(r"(\d+)\s*(?:min|minute|hour|hr)", text_l)
        if playtime_match:
            value = int(playtime_match.group(1))
            if "hour" in text_l or "hr" in text_l:
                value = value * 60
            cons.setdefault("playtime", {})["target"] = value
            cons.setdefault("playtime", {})["tolerance"] = 0.3

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
