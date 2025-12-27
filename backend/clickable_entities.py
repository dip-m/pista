"""
Utility functions for extracting clickable entities from chat responses.
"""
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ClickableEntity(BaseModel):
    type: str  # "game", "designer", "artist", "mechanic", "category"
    id: Optional[int] = None
    name: str
    start_pos: int  # Character position in reply_text where entity starts
    end_pos: int  # Character position in reply_text where entity ends


def extract_clickable_entities(reply_text: str, results: Optional[List[Dict[str, Any]]] = None) -> List[ClickableEntity]:
    """
    Extract clickable entities (games, designers, artists) from reply_text and results.

    Args:
        reply_text: The chat reply text
        results: List of game results that may contain entities

    Returns:
        List of ClickableEntity objects with positions in reply_text
    """
    entities = []

    if not results:
        return entities

    # Build a map of names to IDs from results
    name_to_id = {}
    name_to_type = {}

    for result in results:
        # Game names
        if "name" in result and "game_id" in result:
            game_name = result["name"]
            game_id = result["game_id"]
            name_to_id[game_name.lower()] = game_id
            name_to_type[game_name.lower()] = "game"

        # Designers
        if "designers" in result:
            designers = result["designers"]
            if isinstance(designers, list):
                for designer in designers:
                    if isinstance(designer, str):
                        name_to_id[designer.lower()] = None  # Designer ID not always available
                        name_to_type[designer.lower()] = "designer"
            elif isinstance(designers, dict) and "id" in designers:
                designer_name = designers.get("name", "")
                if designer_name:
                    name_to_id[designer_name.lower()] = designers.get("id")
                    name_to_type[designer_name.lower()] = "designer"

        # Artists (if available in results)
        if "artists" in result:
            artists = result["artists"]
            if isinstance(artists, list):
                for artist in artists:
                    if isinstance(artist, str):
                        name_to_id[artist.lower()] = None
                        name_to_type[artist.lower()] = "artist"

    # Find all entity names in reply_text (case-insensitive)
    reply_lower = reply_text.lower()

    for name_lower, entity_id in name_to_id.items():
        entity_type = name_to_type.get(name_lower, "game")

        # Find all occurrences of this name in the text
        # Use word boundaries to avoid partial matches
        pattern = rf"\b{re.escape(name_lower)}\b"
        for match in re.finditer(pattern, reply_lower, re.IGNORECASE):
            # Find the actual case in the original text
            start_pos = match.start()
            end_pos = match.end()
            actual_name = reply_text[start_pos:end_pos]

            entities.append(
                ClickableEntity(type=entity_type, id=entity_id, name=actual_name, start_pos=start_pos, end_pos=end_pos)
            )

    # Sort by position to avoid overlapping issues
    entities.sort(key=lambda e: e.start_pos)

    # Remove overlapping entities (keep the longer one)
    filtered_entities = []
    for entity in entities:
        # Check if this entity overlaps with any already added
        overlaps = False
        for existing in filtered_entities:
            if not (entity.end_pos <= existing.start_pos or entity.start_pos >= existing.end_pos):
                # Overlaps - keep the longer one
                if (entity.end_pos - entity.start_pos) > (existing.end_pos - existing.start_pos):
                    # Replace existing with this one
                    filtered_entities.remove(existing)
                    filtered_entities.append(entity)
                overlaps = True
                break
        if not overlaps:
            filtered_entities.append(entity)

    return filtered_entities
