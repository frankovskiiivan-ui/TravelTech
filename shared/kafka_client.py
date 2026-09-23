"""Обертка над Kafka (pub/sub)"""
import asyncio
from typing import Callable, Dict, List
from shared.logger import get_logger

logger = get_logger("Kafka")


class KafkaClient:
    """In-memory мок Kafka"""
    
    def __init__(self):
        self._topics: Dict[str, List[Callable]] = {}
        logger.info("Kafka producer connected")

    async def publish(self, topic: str, message: dict) -> None:
        logger.info(f"PUBLISH topic={topic} event={message.get('event')}")
        handlers = self._topics.get(topic, [])
        for handler in handlers:
            # Fire-and-forget, как в реальной Kafka
            asyncio.create_task(handler(message))

    def subscribe(self, topic: str, handler: Callable) -> None:
        self._topics.setdefault(topic, []).append(handler)
        logger.info(f"SUBSCRIBED to topic={topic}")