"""Обертка над PostgreSQL"""
from typing import Any, Dict, Optional
from shared.logger import get_logger

logger = get_logger("PostgreSQL")


class Database:
    """
    В продакшене здесь был бы asyncpg или SQLAlchemy.
    Сейчас — in-memory мок для демонстрации.
    """
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
        logger.info("Database connection established")

    async def save_trip(self, trip_id: str, data: Dict[str, Any]) -> None:
        logger.info(f"SAVE trip_id={trip_id} status={data.get('status')}")
        self._storage[trip_id] = data

    async def get_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        logger.info(f"GET trip_id={trip_id}")
        return self._storage.get(trip_id)

    async def update_trip(self, trip_id: str, updates: Dict[str, Any]) -> None:
        if trip_id in self._storage:
            self._storage[trip_id].update(updates)
            logger.info(f"UPDATE trip_id={trip_id} -> {updates}")

    async def close(self):
        logger.info("Database connection closed")