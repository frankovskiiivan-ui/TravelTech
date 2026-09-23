"""Точка входа Recommendation Service"""
import asyncio
from shared.logger import get_logger
from services.recommendation_service.personalizer import RecommendationService

logger = get_logger("RecommendationService.Main")


async def main():
    logger.info("🚀 Recommendation Service starting...")
    service = RecommendationService()
    
    result = await service.personalize("user_123", "Найден рейс Москва → Париж")
    logger.info(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())