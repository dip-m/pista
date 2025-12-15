# backend/bgg_collection.py
import time
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from backend.logger_config import logger
from functools import lru_cache
import threading

BGG_COLLECTION_URL = "https://boardgamegeek.com/xmlapi2/collection"
BGG_RATE_LIMIT_DELAY = 1.0  # Minimum seconds between requests
_last_request_time = 0
_rate_limit_lock = threading.Lock()

headers = {
    "Authorization": f"Bearer f8b71467-0069-4536-a822-1f3dd0dd431c",
    "Accept": "application/json",
}


def _rate_limit():
    """Enforce rate limiting for BGG API calls."""
    global _last_request_time
    with _rate_limit_lock:
        elapsed = time.time() - _last_request_time
        if elapsed < BGG_RATE_LIMIT_DELAY:
            sleep_time = BGG_RATE_LIMIT_DELAY - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        _last_request_time = time.time()


def fetch_user_collection(bgg_user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch a user's collection from BGG API with personal ratings.
    Returns list of dicts with game_id and personal_rating.
    """
    logger.info(f"Fetching BGG collection for user: {bgg_user_id}")
    
    # Sanitize input
    bgg_user_id = bgg_user_id.strip()
    if not bgg_user_id:
        raise ValueError("BGG user ID cannot be empty")
    
    params = {
        "username": bgg_user_id,
        "own": "1",  # Only owned games
        "stats": "1"
    }
    
    max_retries = 5
    retry_sleep = 5.0
    
    for attempt in range(max_retries):
        try:
            _rate_limit()  # Enforce rate limiting
            resp = requests.get(BGG_COLLECTION_URL, params=params, headers = headers, timeout=30)
            
            if resp.status_code == 202:
                logger.debug(f"BGG request queued, waiting {retry_sleep}s (attempt {attempt + 1})")
                time.sleep(retry_sleep)
                continue
            
            if resp.status_code != 200:
                logger.warning(f"BGG API returned status {resp.status_code} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(retry_sleep)
                    continue
                raise Exception(f"BGG API returned status {resp.status_code}")
            
            try:
                root = ET.fromstring(resp.content)
            except ET.ParseError as e:
                logger.error(f"Failed to parse BGG XML: {e}")
                raise
            
            games = []
            for item in root.findall("item"):
                game_id = item.get("objectid")
                if not game_id:
                    continue
                
                try:
                    game_id_int = int(game_id)
                except ValueError:
                    logger.debug(f"Invalid game_id: {game_id}")
                    continue
                
                # Extract personal rating from stats/rating/value
                personal_rating = None
                stats = item.find("stats")
                if stats is not None:
                    rating = stats.find("rating")
                    if rating is not None:
                        value_elem = rating.find("value")
                        if value_elem is not None and value_elem.text:
                            try:
                                # BGG ratings are stored as strings, "N/A" if not rated
                                rating_str = value_elem.text.strip()
                                if rating_str and rating_str != "N/A":
                                    personal_rating = float(rating_str)
                            except (ValueError, AttributeError):
                                pass
                
                games.append({
                    "game_id": game_id_int,
                    "personal_rating": personal_rating
                })
            
            logger.info(f"Fetched {len(games)} games from BGG collection for user {bgg_user_id}")
            return games
            
        except requests.RequestException as e:
            logger.warning(f"Request error fetching BGG collection (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_sleep)
                continue
            raise
    
    raise Exception(f"Failed to fetch BGG collection after {max_retries} attempts")

