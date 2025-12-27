"""
Rulebook Parser Module
Parses game rulebooks to extract scoring criteria and mechanisms.
"""
import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def parse_scoring_criteria(rulebook_text: str) -> Dict[str, Any]:
    """
    Parse rulebook text to extract scoring criteria.

    Returns a dictionary with:
    - criteria: List of scoring criteria with labels, types, and formulas
    - intermediate_scores: List of intermediate scoring steps
    - final_score_formula: Formula for calculating final score
    """
    if not rulebook_text:
        return {"criteria": [], "intermediate_scores": [], "final_score_formula": "sum", "confidence": 0.0}

    rulebook_lower = rulebook_text.lower()
    criteria = []
    intermediate_scores = []
    confidence = 0.0

    # Pattern 1: Look for explicit scoring sections
    scoring_section_patterns = [
        r"scoring[:\s]+(.*?)(?=\n\n|\n[A-Z][a-z]+:|$)",
        r"end.*?game.*?scoring[:\s]+(.*?)(?=\n\n|\n[A-Z][a-z]+:|$)",
        r"victory.*?points[:\s]+(.*?)(?=\n\n|\n[A-Z][a-z]+:|$)",
        r"points[:\s]+(.*?)(?=\n\n|\n[A-Z][a-z]+:|$)",
    ]

    scoring_text = ""
    for pattern in scoring_section_patterns:
        match = re.search(pattern, rulebook_lower, re.IGNORECASE | re.DOTALL)
        if match:
            scoring_text = match.group(1)
            confidence += 0.3
            break

    if not scoring_text:
        # Try to find scoring mentions throughout the text
        scoring_text = rulebook_text
        confidence += 0.1

    # Pattern 2: Extract point values and conditions
    # Look for patterns like "X points for Y", "score X points", "worth X points"
    point_patterns = [
        r"(\d+)\s*points?\s+(?:for|per|when|if|by)\s+([^\.]+)",
        r"score\s+(\d+)\s*points?\s+(?:for|per|when|if|by)\s+([^\.]+)",
        r"worth\s+(\d+)\s*points?\s+(?:for|per|when|if|by)\s+([^\.]+)",
        r"(\d+)\s*vp\s+(?:for|per|when|if|by)\s+([^\.]+)",
        r"(\d+)\s*victory\s+points?\s+(?:for|per|when|if|by)\s+([^\.]+)",
    ]

    found_criteria = []
    for pattern in point_patterns:
        matches = re.finditer(pattern, scoring_text, re.IGNORECASE)
        for match in matches:
            points = int(match.group(1))
            condition = match.group(2).strip()

            # Determine input type based on condition
            input_type = "number"
            if any(word in condition.lower() for word in ["card", "tile", "token", "piece"]):
                input_type = "number"
            elif any(word in condition.lower() for word in ["set", "group", "collection"]):
                input_type = "number"
            elif any(word in condition.lower() for word in ["area", "region", "territory"]):
                input_type = "number"
            elif any(word in condition.lower() for word in ["resource", "money", "gold", "coin"]):
                input_type = "number"
            else:
                input_type = "number"  # Default to number

            found_criteria.append(
                {
                    "label": condition[:100],  # Limit length
                    "points": points,
                    "input_type": input_type,
                    "formula": f"{points} * value",  # Simple formula
                    "description": condition,
                }
            )
            confidence += 0.1

    # Pattern 3: Look for multipliers or bonuses
    multiplier_patterns = [
        r"(\d+)x\s+([^\.]+)",
        r"double\s+([^\.]+)",
        r"triple\s+([^\.]+)",
        r"bonus\s+of\s+(\d+)\s+points?\s+for\s+([^\.]+)",
    ]

    for pattern in multiplier_patterns:
        matches = re.finditer(pattern, scoring_text, re.IGNORECASE)
        for match in matches:
            if "double" in pattern or "triple" in pattern:
                multiplier = 2 if "double" in pattern else 3
                condition = match.group(1).strip()
            else:
                multiplier = int(match.group(1))
                condition = match.group(2).strip()

            found_criteria.append(
                {
                    "label": f"{multiplier}x {condition[:80]}",
                    "points": multiplier,
                    "input_type": "number",
                    "formula": f"{multiplier} * value",
                    "description": condition,
                }
            )
            confidence += 0.05

    # Pattern 4: Look for end-game conditions
    end_game_patterns = [
        r"at\s+the\s+end\s+of\s+the\s+game[,\s]+([^\.]+)",
        r"final\s+scoring[:\s]+(.*?)(?=\n\n|$)",
        r"end\s+game\s+scoring[:\s]+(.*?)(?=\n\n|$)",
    ]

    for pattern in end_game_patterns:
        matches = re.finditer(pattern, scoring_text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            end_game_text = match.group(1).strip()
            # Try to extract criteria from end-game text
            point_matches = re.finditer(r"(\d+)\s*points?\s+(?:for|per)\s+([^\.]+)", end_game_text, re.IGNORECASE)
            for pm in point_matches:
                points = int(pm.group(1))
                condition = pm.group(2).strip()
                found_criteria.append(
                    {
                        "label": f"End-game: {condition[:80]}",
                        "points": points,
                        "input_type": "number",
                        "formula": f"{points} * value",
                        "description": condition,
                        "is_end_game": True,
                    }
                )
                confidence += 0.1

    # Remove duplicates based on label similarity
    unique_criteria = []
    seen_labels = set()
    for crit in found_criteria:
        label_key = crit["label"].lower()[:50]  # Use first 50 chars for comparison
        if label_key not in seen_labels:
            unique_criteria.append(crit)
            seen_labels.add(label_key)

    # Limit to top 10 criteria by confidence (points value as proxy)
    unique_criteria.sort(key=lambda x: x.get("points", 0), reverse=True)
    unique_criteria = unique_criteria[:10]

    # If we found criteria, create intermediate scores
    if unique_criteria:
        for i, crit in enumerate(unique_criteria):
            intermediate_scores.append(
                {"id": f"score_{i+1}", "label": crit["label"], "formula": crit["formula"], "input_type": crit["input_type"]}
            )

    # Determine final score formula
    # Default to sum, but could be more complex
    final_score_formula = "sum"  # Simple sum of all intermediate scores

    # Check if there are any special final scoring rules
    if re.search(r"highest.*?wins|most.*?points.*?wins", rulebook_lower):
        final_score_formula = "sum"
    elif re.search(r"lowest.*?wins|fewest.*?points.*?wins", rulebook_lower):
        final_score_formula = "sum"  # Still sum, but winner is lowest

    # Normalize confidence
    confidence = min(confidence, 1.0)

    return {
        "criteria": unique_criteria,
        "intermediate_scores": intermediate_scores,
        "final_score_formula": final_score_formula,
        "confidence": confidence,
        "source_text_snippet": scoring_text[:500] if scoring_text else None,
    }


def extract_scoring_from_rulebook(game_id: int, rulebook_text: str) -> Dict[str, Any]:
    """
    Extract scoring mechanism from rulebook and return structured data.
    This is called when a rulebook is processed.
    """
    if not rulebook_text:
        return None

    parsed = parse_scoring_criteria(rulebook_text)

    if parsed["confidence"] < 0.2 or len(parsed["criteria"]) == 0:
        # Low confidence or no criteria found
        return None

    return {"game_id": game_id, "criteria_json": json.dumps(parsed), "status": "pending", "confidence": parsed["confidence"]}
