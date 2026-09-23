"""Точка входа Notification Service"""
import asyncio
from shared.kafka_client import KafkaClient
from shared.logger import get_logger
from services.notification_service.handler import NotificationService
from services.recommendation_service.personalizer import RecommendationService

logger = get_logger("NotificationService.Main")


async def main():
    logger.info("🚀 Notification Service starting...")
    
    kafka = KafkaClient()
    recommendation = RecommendationService()
    
    # Регистрируем обработчик — он подпишется на Kafka
    NotificationService(kafka, recommendation)
    
    # В реальности тут был бы consumer loop; для демо — просто ждем
    logger.info("Waiting for events...")
    await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())