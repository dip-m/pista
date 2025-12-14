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


def fetch_user_collection(bgg_user_id: str) -> List[int]:
    """
    Fetch a user's collection from BGG API.
    Returns list of game IDs (BGG IDs).
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
            
            game_ids = []
            for item in root.findall("item"):
                game_id = item.get("objectid")
                if game_id:
                    try:
                        game_ids.append(int(game_id))
                    except ValueError:
                        logger.debug(f"Invalid game_id: {game_id}")
            
            logger.info(f"Fetched {len(game_ids)} games from BGG collection for user {bgg_user_id}")
            return game_ids
            
        except requests.RequestException as e:
            logger.warning(f"Request error fetching BGG collection (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_sleep)
                continue
            raise
    
    raise Exception(f"Failed to fetch BGG collection after {max_retries} attempts")

