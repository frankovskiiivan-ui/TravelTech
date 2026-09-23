"""Точка входа Flight Tracker Service"""
import asyncio
from shared.cache import Cache
from shared.logger import get_logger
from services.external_adapters.aviation_api import AviationAPI
from services.flight_tracker.tracker import FlightTracker

logger = get_logger("FlightTracker.Main")


async def main():
    logger.info("🚀 Flight Tracker Service starting...")
    
    cache = Cache()
    aviation_api = AviationAPI()
    tracker = FlightTracker(cache, aviation_api)
    
    # Демонстрация работы
    status = await tracker.get_status("SU1234")
    logger.info(f"Result: {status}")


if __name__ == "__main__":
    asyncio.run(main())