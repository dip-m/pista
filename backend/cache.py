# backend/cache.py
from functools import lru_cache
from typing import Dict, Any, List
import time
from backend.logger_config import logger

# Simple in-memory cache with TTL
_cache: Dict[str, tuple[Any, float]] = {}
CACHE_TTL = 300  # 5 minutes


def get_cached(key: str) -> Any:
    """Get value from cache if not expired."""
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            logger.debug(f"Cache hit: {key}")
            return value
        else:
            logger.debug(f"Cache expired: {key}")
            del _cache[key]
    return None


def set_cached(key: str, value: Any) -> None:
    """Set value in cache with current timestamp."""
    _cache[key] = (value, time.time())
    logger.debug(f"Cache set: {key}")


def clear_cache() -> None:
    """Clear all cache entries."""
    _cache.clear()
    logger.info("Cache cleared")
