"""Обертка над Redis (кэш)"""
import time
from typing import Any, Optional
from shared.logger import get_logger

logger = get_logger("Redis")


class Cache:
    """In-memory мок Redis с поддержкой TTL"""
    
    def __init__(self):
        self._cache: dict = {}
        logger.info("Redis connection established")

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        expires_at = time.time() + ttl
        self._cache[key] = (value, expires_at)
        logger.info(f"SET {key} (ttl={ttl}s)")

    async def get(self, key: str) -> Optional[Any]:
        item = self._cache.get(key)
        if not item:
            logger.info(f"MISS {key}")
            return None
        
        value, expires_at = item
        if time.time() > expires_at:
            del self._cache[key]
            logger.info(f"EXPIRED {key}")
            return None
        
        logger.info(f"HIT {key}")
        return value

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)
        logger.info(f"DEL {key}")