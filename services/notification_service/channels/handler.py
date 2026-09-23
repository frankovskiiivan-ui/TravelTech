"""Обработчик событий из Kafka"""
from shared.logger import get_logger
from services.notification_service.channels.push import send_push
from services.notification_service.channels.email import send_email
from services.notification_service.channels.sms import send_sms

logger = get_logger("NotificationService.Handler")


class NotificationService:
    def __init__(self, kafka, recommendation_service):
        self.kafka = kafka
        self.recommendation = recommendation_service
        kafka.subscribe("trip_events", self.handle_event)

    async def handle_event(self, message: dict) -> None:
        event = message.get("event")
        user_id = message.get("user_id")
        
        logger.info(f"Received event: {event} for user={user_id}")
        
        if event == "offer_created":
            await self._notify_offer(user_id, message)
        elif event == "payment_success":
            await self._notify_payment(user_id, message)

    async def _notify_offer(self, user_id: str, message: dict) -> None:
        base_text = f"Найден новый вариант поездки! Вариантов: {message.get('offers_count')}"
        
        # Персонализация через ML
        text = await self.recommendation.personalize(user_id, base_text)
        
        await send_push(user_id, text)
        await send_email(user_id, text)

    async def _notify_payment(self, user_id: str, message: dict) -> None:
        base_text = "Оплата прошла успешно! Приятного путешествия ✈️"
        text = await self.recommendation.personalize(user_id, base_text)
        
        await send_push(user_id, text)
        await send_sms(user_id, text)