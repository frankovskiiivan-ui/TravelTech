"""Диспетчер (Trip Service) — сердце системы"""
from typing import Dict, Any, Optional
from shared.logger import get_logger
from services.trip_service.alternative_search import AlternativeSearch

logger = get_logger("TripService.Dispatcher")


class TripServiceDispatcher:
    """Оркестратор всех операций с поездками"""

    def __init__(self, adapters: Dict[str, Any], db: Any, kafka: Any):
        self.adapters = adapters
        self.db = db
        self.kafka = kafka
        self.search = AlternativeSearch(adapters)

    @staticmethod
    def _get_required_field(payload: Dict[str, Any], field: str) -> Any:
        """Безопасная проверка обязательного поля."""
        if field not in payload:
            raise ValueError(f"Missing required field in payload: {field}")
        return payload[field]

    async def handle_flight_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Узнать статус рейса"""
        flight_number = self._get_required_field(payload, "flight_number")
        logger.info(f"Handle flight status: flight_number={flight_number}")

        try:
            result = await self.adapters["aviation"].get_flight_status(flight_number)
            return result
        except Exception as e:
            logger.error(f"Failed to get flight status for {flight_number}: {e}", exc_info=True)
            raise

    async def handle_find_offer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Найти альтернативный вариант (поиск)"""
        user_id = self._get_required_field(payload, "user_id")
        logger.info(f"Handle find offer for user={user_id}")

        # 1. Ищем альтернативы
        alternatives = await self.search.find(payload)

        if not alternatives:
            return {"status": "not_found", "offers": []}

        # 2. Сохраняем в БД
        trip_id = f"trip_{user_id}_{len(alternatives)}"
        trip_data = {
            "status": "offer_created",
            "user_id": user_id,
            "alternatives": alternatives,
        }
        await self.db.save_trip(trip_id, trip_data)

        # 3. Публикуем событие в Kafka (для Notification Service)
        kafka_event = {
            "event": "offer_created",
            "trip_id": trip_id,
            "user_id": user_id,
            "offers_count": len(alternatives),
        }
        await self.kafka.publish("trip_events", kafka_event)

        return {
            "trip_id": trip_id,
            "status": "offer_created",
            "offers": alternatives,
        }

    async def handle_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Запрос на оплату"""
        trip_id = self._get_required_field(payload, "trip_id")
        logger.info(f"Handle payment for trip={trip_id}")

        # 1. Вызов платежного шлюза
        payment_result = await self.adapters["payment"].process_payment(payload)

        # 2. Обновляем БД и публикуем событие, если оплата успешна
        if payment_result.get("status") == "success":
            await self.db.update_trip(trip_id, {"status": "paid"})

            kafka_event = {
                "event": "payment_success",
                "trip_id": trip_id,
                "user_id": payload.get("user_id"),
            }
            await self.kafka.publish("trip_events", kafka_event)

        return payment_result
