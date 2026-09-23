"""Логика отслеживания статуса рейсов"""
from typing import Dict
from shared.logger import get_logger

logger = get_logger("FlightTracker")


class FlightTracker:
    """Опрашивает внешние авиа-API для получения статуса рейса"""
    
    def __init__(self, cache, aviation_api):
        self.cache = cache
        self.aviation_api = aviation_api

    async def get_status(self, flight_number: str) -> Dict:
        """Узнать статус рейса (с кэшированием в Redis)"""
        cache_key = f"flight_status:{flight_number}"
        
        # 1. Проверяем кэш
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {flight_number}")
            return cached
        
        # 2. Запрос к внешнему API
        status = await self.aviation_api.get_flight_status(flight_number)
        
        # 3. Сохраняем в кэш на 5 минут
        await self.cache.set(cache_key, status, ttl=300)
        
        return status