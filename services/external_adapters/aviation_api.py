"""Адаптер для Авиа API"""
import asyncio
from typing import Dict, List
from shared.logger import get_logger
from services.external_adapters.base import BaseAdapter

logger = get_logger("AviationAPI")


class AviationAPI(BaseAdapter):
    def __init__(self):
        super().__init__(base_url="https://api.aviation.mock")

    async def search_flights(self, params: Dict) -> List[Dict]:
        logger.info(f"[Aviation API] Search flights: {params}")
        await asyncio.sleep(0.3)  # Имитация сети
        return [
            {"id": "FL001", "airline": "Aeroflot", "price": 15000, "duration": "3h 30m"},
            {"id": "FL002", "airline": "S7", "price": 12500, "duration": "3h 45m"},
        ]

    async def get_flight_status(self, flight_number: str) -> Dict:
        logger.info(f"[Aviation API] Get flight status: {flight_number}")
        await asyncio.sleep(0.2)
        return {
            "flight_number": flight_number,
            "status": "on_time",
            "departure": "SVO 10:30",
            "arrival": "CDG 13:00"
        }