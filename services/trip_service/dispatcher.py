"""
Trip Dispatcher — новый сценарий:
1. search_flights(city_from, city_to, date)  → список рейсов
2. book_trip(user_id, flight_iata, passengers) → бронирование + отели
"""
import uuid
from shared.logger import get_logger
from shared.database import db
from shared.kafka_client import kafka
from shared.config import settings
from services.external_adapters.search_flights_adapter import SearchFlightsAdapter
from services.external_adapters.staying_api_adapter import StayingAPIAdapter

log = get_logger("trip_dispatcher")

flight_api = SearchFlightsAdapter()
hotel_api = StayingAPIAdapter()


class TripServiceDispatcher:

    # ─────────────────────────────────────────────
    # Шаг 1: поиск рейсов
    # ─────────────────────────────────────────────
    async def search_flights(
        self, city_from: str, city_to: str, date: str | None = None
    ) -> list[dict]:
        flights = await flight_api.search_flights(city_from, city_to, date)
        available = [f for f in flights if f.get("seats_left", 0) > 0]
        log.info(f"Search: {city_from}→{city_to}, всего {len(flights)}, доступно {len(available)}")
        return available

    # ─────────────────────────────────────────────
    # Шаг 2: бронирование рейса + поиск отелей
    # ─────────────────────────────────────────────
    async def book_trip(
        self, user_id: str, flight_iata: str, passengers: int
    ) -> dict:
        trip_id = f"TRIP-{uuid.uuid4().hex[:8].upper()}"

        if not flight_iata:
            return {
                "trip_id": trip_id, "user_id": user_id,
                "status": "ERROR",
                "message": "Не указан рейс для бронирования.",
            }

        # Проверяем рейс
        flight_data = await flight_api.get_flight_by_iata(flight_iata)
        if not flight_data:
            return {
                "trip_id": trip_id, "user_id": user_id,
                "status": "FLIGHT_NOT_FOUND",
                "message": "Рейс не найден.",
            }

        seats_left = flight_data.get("seats_left", 0)
        if seats_left < passengers:
            return {
                "trip_id": trip_id, "user_id": user_id,
                "status": "NO_SEATS",
                "message": f"Недостаточно мест: нужно {passengers}, доступно {seats_left}.",
            }

        # Расчёт стоимости
        price_per_ticket = flight_data.get("price_per_ticket", 0)
        total_price = price_per_ticket * passengers

        # Определяем город прибытия
        arr_iata = flight_data.get("arr_iata", "")
        resolved_city = flight_api.iata_to_city(arr_iata) if arr_iata else None
        if not resolved_city and arr_iata:
            resolved_city = arr_iata  # передаём как есть — StayingAPI попробует найти

        # Ищем отели для города прибытия
        hotels: list[dict] = []
        if resolved_city:
            log.info(f"Searching hotels in {resolved_city} for {trip_id}")
            hotels = await hotel_api.search_hotels(resolved_city)
            log.info(f"Found {len(hotels)} hotels in {resolved_city}")

        # Сохраняем поездку
        trip = {
            "trip_id": trip_id,
            "user_id": user_id,
            "flight": flight_data,
            "passengers": passengers,
            "total_price": total_price,
            "city": resolved_city or "",
            "hotels": hotels,
            "status": "BOOKED_WITH_HOTELS" if hotels else "BOOKED",
        }
        await db.save_trip(trip_id, trip)

        # Уведомление
        msg = (
            f"Рейс {flight_iata} забронирован на {passengers} пас. "
            f"Итого: {total_price} ₽."
        )
        if hotels:
            msg += f" Найдено отелей: {len(hotels)}."
        await self._notify(trip_id, msg)

        return await db.get_trip(trip_id)

    # ─────────────────────────────────────────────
    # Уведомления
    # ─────────────────────────────────────────────
    async def _notify(self, trip_id: str, message: str):
        await kafka.publish(settings.kafka_topic_notifications, {
            "trip_id": trip_id,
            "message": message,
            "channels": ["push", "email"],
        })

    # ─────────────────────────────────────────────
    # Feedback
    # ─────────────────────────────────────────────
    async def handle_feedback(self, message: dict):
        trip_id = message.get("trip_id")
        rating = message.get("rating")
        comment = message.get("comment", "")
        if trip_id and rating is not None:
            await db.save_feedback(trip_id, rating, comment)
            log.info(f"Feedback saved: {trip_id} -> {rating}")


dispatcher = TripServiceDispatcher()
