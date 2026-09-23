"""Диспетчер (Trip Service) — сердце системы"""
from typing import Dict
from shared.logger import get_logger
from services.trip_service.alternative_search import AlternativeSearch

logger = get_logger("TripService.Dispatcher")


class TripServiceDispatcher:
    """Оркестратор всех операций с поездками"""
    
    def __init__(self, adapters: Dict, db, kafka):
        self.adapters = adapters
        self.db = db
        self.kafka = kafka
        self.search = AlternativeSearch(adapters)

    async def handle_flight_status(self, payload: Dict) -> Dict:
        """Узнать статус рейса"""
        logger.info(f"Handle flight status: {payload}")
        flight_number = payload["flight_number"]
        return await self.adapters["aviation"].get_flight_status(flight_number)

    async def handle_find_offer(self, payload: Dict) -> Dict:
        """Найти альтернативный вариант (поиск)"""
        logger.info(f"Handle find offer for user={payload.get('user_id')}")
        
        # 1. Ищем альтернативы
        alternatives = await self.search.find(payload)
        
        if not alternatives:
            return {"status": "not_found", "offers": []}
        
        # 2. Сохраняем в БД
        trip_id = f"trip_{payload['user_id']}_{len(alternatives)}"
        await self.db.save_trip(trip_id, {
            "status": "offer_created",
            "user_id": payload["user_id"],
            "alternatives": alternatives
        })
        
        # 3. Публикуем событие в Kafka (для Notification Service)
        await self.kafka.publish("trip_events", {
            "event": "offer_created",
            "trip_id": trip_id,
            "user_id": payload["user_id"],
            "offers_count": len(alternatives)
        })
        
        return {
            "trip_id": trip_id,
            "status": "offer_created",
            "offers": alternatives
        }

    async def handle_payment(self, payload: Dict) -> Dict:
        """Запрос на оплату"""
        logger.info(f"Handle payment for trip={payload.get('trip_id')}")
        
        # 1. Вызов платежного шлюза
        payment_result = await self.adapters["payment"].process_payment(payload)
        
        # 2. Обновляем БД
        if payment_result["status"] == "success":
            await self.db.update_trip(payload["trip_id"], {"status": "paid"})
            
            # 3. Событие в Kafka
            await self.kafka.publish("trip_events", {
                "event": "payment_success",
                "trip_id": payload["trip_id"],
                "user_id": payload.get("user_id")
            })
        
        return payment_result