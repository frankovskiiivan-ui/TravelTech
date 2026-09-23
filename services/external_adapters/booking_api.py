"""Адаптер для Booking.com API"""
import asyncio
from typing import Dict, List
from shared.logger import get_logger
from services.external_adapters.base import BaseAdapter

logger = get_logger("BookingAPI")


class BookingAPI(BaseAdapter):
    def __init__(self):
        super().__init__(base_url="https://api.booking.mock")

    async def search_hotels(self, params: Dict) -> List[Dict]:
        logger.info(f"[Booking API] Search hotels: {params}")
        await asyncio.sleep(0.4)
        return [
            {"id": "HT001", "name": "Hilton Paris", "price": 12000, "rating": 4.8},
            {"id": "HT002", "name": "Ibis Paris", "price": 6500, "rating": 4.1},
        ]