"""Точка входа Trip Service"""
import asyncio
from shared.database import Database
from shared.kafka_client import KafkaClient
from shared.logger import get_logger
from services.external_adapters.aviation_api import AviationAPI
from services.external_adapters.booking_api import BookingAPI
from services.external_adapters.payment_api import PaymentAPI
from services.trip_service.dispatcher import TripServiceDispatcher

logger = get_logger("TripService.Main")


async def main():
    logger.info("🚀 Trip Service starting...")
    
    # Инициализация зависимостей
    db = Database()
    kafka = KafkaClient()
    
    adapters = {
        "aviation": AviationAPI(),
        "booking": BookingAPI(),
        "payment": PaymentAPI()
    }
    
    dispatcher = TripServiceDispatcher(adapters, db, kafka)
    
    # Демонстрация работы
    result = await dispatcher.handle_find_offer({
        "user_id": "user_123",
        "origin": "Moscow",
        "destination": "Paris"
    })
    logger.info(f"Result: {result}")
    
    # Даем Kafka время доставить сообщения
    await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())