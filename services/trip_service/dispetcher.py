import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import asyncpg
import redis.asyncio as redis
from kafka import KafkaConsumer, KafkaProducer
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, Column, String, Integer, DateTime, Boolean, JSON

from shared.models import Trip, TripFlight, TripChange
from shared.kafka_consumer import KafkaConsumerWrapper
from shared.redis_client import get_redis

# --- Конфигурация ---
import os
#Настраиваем подключение к базе данных PostgreSQL, Redis, Kafka
DB_URL = os.getenv("DB_URL", "postgresql+asyncpg://user:pass@postgres:5432/traveltech")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")

logger = logging.getLogger(__name__)

# --- База данных ---
engine = create_async_engine(DB_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# --- Модели (в реальном проекте — в shared/models.py) ---

#Опишем структуру таблиц в PostgreSQL.
# 1. Пользователь
class TripModel(Base):
    __tablename__ = "trips"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    status = Column(String, default="active")
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#2. FlightTracker, Alternative Service, Payment Service 
class TripFlightModel(Base):
    __tablename__ = "trip_flights"
    id = Column(String, primary_key=True)
    trip_id = Column(String, nullable=False)
    flight_number = Column(String, nullable=False)
    airline = Column(String)
    departure = Column(DateTime)
    arrival = Column(DateTime)
    status = Column(String, default="scheduled")
    baggage = Column(Boolean, default=False)
    visa_required = Column(Boolean, default=False)


# --- Основная логика Диспетчера ---
class TripDispatcher:
    def __init__(self):
        self.kafka_consumer = None
        self.kafka_producer = None
        self.redis_client = None

    async def initialize(self):
        """Инициализация подключений"""
        self.redis_client = await get_redis()
        
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        self.kafka_consumer = KafkaConsumerWrapper(
            topic="flight_status",
            bootstrap_servers=KAFKA_BROKERS,
            group_id="trip-service-group",
            callback=self.handle_flight_status
        )

    async def handle_flight_status(self, event: Dict[str, Any]):
        """
        Обрабатывает событие о задержке/отмене рейса.
        Это главная точка входа для Диспетчера.
        """
        flight_id = event.get("flight_id")
        new_status = event.get("status")
        delay_minutes = event.get("delay_minutes", 0)

        logger.info(f"📡 Получено событие: рейс {flight_id} -> {new_status}")

        # 1. Находим поездку, к которой относится этот рейс
        trip = await self._find_trip_by_flight(flight_id)
        if not trip:
            logger.warning(f"⚠️ Рейс {flight_id} не найден ни в одной поездке")
            return

        # 2. Проверяем стыковки
        next_flight = await self._get_next_flight(trip.id, flight_id)
        
        if next_flight:
            connection_time = (next_flight.departure - next_flight.arrival).total_seconds() / 60
            new_connection_time = connection_time - delay_minutes

            logger.info(f"🔄 Стыковка: было {connection_time} мин, стало {new_connection_time} мин")

            # 3. Если стыковка нарушена (меньше 20 минут)
            if new_connection_time < 20:
                logger.info(f"🔴 Стыковка нарушена! Ищем альтернативу...")
                
                # 3.1 Запрашиваем альтернативу через Alternative Service
                alternative = await self._request_alternative(trip, flight_id, delay_minutes)
                
                if alternative:
                    # 3.2 Обновляем маршрут
                    await self._update_trip_with_alternative(trip, flight_id, alternative)
                    
                    # 3.3 Отправляем уведомление
                    await self._notify_trip_updated(trip, alternative)
                else:
                    # 3.4 Альтернатив нет — просто уведомляем о задержке
                    await self._notify_delay_only(trip, flight_id, delay_minutes)
                
                return

        # 4. Если стыковка не нарушена — просто обновляем статус
        await self._update_flight_status(flight_id, new_status, delay_minutes)
        await self._notify_delay_only(trip, flight_id, delay_minutes)

        logger.info(f"✅ Обработка события завершена")

    async def _find_trip_by_flight(self, flight_id: str) -> Optional[TripModel]:
        """Находит поездку по ID рейса"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT t.* FROM trips t JOIN trip_flights tf ON t.id = tf.trip_id WHERE tf.id = :flight_id"),
                {"flight_id": flight_id}
            )
            row = result.first()
            if row:
                return TripModel(**row._mapping)
            return None

    async def _get_next_flight(self, trip_id: str, current_flight_id: str) -> Optional[TripFlightModel]:
        """Находит следующий рейс после текущего"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM trip_flights 
                    WHERE trip_id = :trip_id AND id != :current_id 
                    ORDER BY departure ASC LIMIT 1
                """),
                {"trip_id": trip_id, "current_id": current_flight_id}
            )
            row = result.first()
            if row:
                return TripFlightModel(**row._mapping)
            return None

    async def _request_alternative(self, trip: TripModel, flight_id: str, delay_minutes: int) -> Optional[Dict]:
        """Запрашивает альтернативу через Alternative Service (HTTP-вызов)"""
        import aiohttp
        
        alternative_url = "http://alternative_service:8000/api/v1/search"
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "trip_id": trip.id,
                "flight_id": flight_id,
                "delay_minutes": delay_minutes,
                "baggage": True,  # можно загрузить из базы
                "visa_required": False,
                "timezone_offset": 3
            }
            
            async with session.post(alternative_url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"❌ Alternative Service вернул ошибку: {response.status}")
                    return None

    async def _update_trip_with_alternative(self, trip: TripModel, old_flight_id: str, alternative: Dict):
        """Обновляет план поездки новой альтернативой"""
        async with AsyncSessionLocal() as session:
            # 1. Отмечаем старый рейс как заменённый
            await session.execute(
                text("UPDATE trip_flights SET status = 'replaced' WHERE id = :flight_id"),
                {"flight_id": old_flight_id}
            )
            
            # 2. Добавляем новый рейс
            new_flight = TripFlightModel(
                id=f"FL{datetime.utcnow().timestamp()}",
                trip_id=trip.id,
                flight_number=alternative["flight_number"],
                airline=alternative["airline"],
                departure=datetime.fromisoformat(alternative["departure"]),
                arrival=datetime.fromisoformat(alternative["arrival"]),
                status="scheduled",
                baggage=trip.baggage,
                visa_required=trip.visa_required
            )
            session.add(new_flight)
            
            # 3. Сохраняем историю изменений
            change = TripChange(
                id=f"CH{datetime.utcnow().timestamp()}",
                trip_id=trip.id,
                old_value={"flight_id": old_flight_id},
                new_value={"flight_id": alternative["flight_id"]},
                reason="delay_replacement"
            )
            session.add(change)
            
            # 4. Обновляем статус всей поездки
            await session.execute(
                text("UPDATE trips SET status = 'updated', updated_at = NOW() WHERE id = :trip_id"),
                {"trip_id": trip.id}
            )
            
            await session.commit()
            
            # 5. Обновляем кеш в Redis
            await self.redis_client.setex(
                f"trip:{trip.id}:status",
                3600,
                "updated"
            )
            
            logger.info(f"✅ План поездки {trip.id} обновлён: {old_flight_id} -> {alternative['flight_number']}")

    async def _notify_trip_updated(self, trip: TripModel, alternative: Dict):
        """Отправляет уведомление об обновлении маршрута"""
        event = {
            "trip_id": trip.id,
            "user_id": trip.user_id,
            "type": "trip_updated",
            "new_flight": alternative,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.kafka_producer.send("trip_updated", value=event)
        self.kafka_producer.flush()
        
        logger.info(f"📤 Отправлено событие trip_updated для поездки {trip.id}")

    async def _notify_delay_only(self, trip: TripModel, flight_id: str, delay_minutes: int):
        """Отправляет уведомление только о задержке (без альтернативы)"""
        event = {
            "trip_id": trip.id,
            "user_id": trip.user_id,
            "type": "flight_delayed",
            "flight_id": flight_id,
            "delay_minutes": delay_minutes,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.kafka_producer.send("flight_delayed", value=event)
        self.kafka_producer.flush()

    async def _update_flight_status(self, flight_id: str, status: str, delay_minutes: int):
        """Обновляет статус рейса в базе данных"""
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE trip_flights 
                    SET status = :status, delay_minutes = :delay, updated_at = NOW() 
                    WHERE id = :flight_id
                """),
                {"status": status, "delay": delay_minutes, "flight_id": flight_id}
            )
            await session.commit()

    async def handle_user_decision(self, trip_id: str, user_id: str, decision: str, selected_flight: str = None):
        """
        Обрабатывает решение пользователя (подтвердить/отклонить).
        Это метод, который вызывается из API Gateway.
        """
        logger.info(f"👤 Пользователь {user_id} принял решение для поездки {trip_id}: {decision}")

        async with AsyncSessionLocal() as session:
            # 1. Проверяем, что пользователь владелец поездки
            trip = await session.execute(
                text("SELECT * FROM trips WHERE id = :trip_id AND user_id = :user_id"),
                {"trip_id": trip_id, "user_id": user_id}
            )
            trip_row = trip.first()
            if not trip_row:
                raise ValueError("User does not own this trip")

            # 2. Сохраняем решение
            await session.execute(
                text("""
                    INSERT INTO trip_decisions (id, trip_id, user_id, decision, selected_flight, made_at)
                    VALUES (gen_random_uuid(), :trip_id, :user_id, :decision, :selected, NOW())
                """),
                {"trip_id": trip_id, "user_id": user_id, "decision": decision, "selected": selected_flight}
            )

            # 3. Если подтверждено — фиксируем статус
            if decision == "accept" and selected_flight:
                await session.execute(
                    text("UPDATE trips SET status = 'confirmed', updated_at = NOW() WHERE id = :trip_id"),
                    {"trip_id": trip_id}
                )
                # Отправляем событие в Kafka
                self.kafka_producer.send("trip_confirmed", value={
                    "trip_id": trip_id,
                    "user_id": user_id,
                    "selected_flight": selected_flight
                })
                self.kafka_producer.flush()
            
            await session.commit()

            # 4. Обновляем кеш
            await self.redis_client.setex(f"trip:{trip_id}:decision", 3600, decision)

            return {"status": "ok", "decision": decision}


#FastAPI приложение для Trip Service 
app = FastAPI(title="Trip Service (Dispatcher)")

dispatcher = TripDispatcher()

@app.on_event("startup")
async def startup():
    await dispatcher.initialize()

@app.post("/api/v1/trips/{trip_id}/decide")
async def decide_trip(
    trip_id: str,
    user_id: str,
    decision: str,
    selected_flight: str = None
):
    """Эндпоинт для принятия решения пользователем"""
    try:
        result = await dispatcher.handle_user_decision(trip_id, user_id, decision, selected_flight)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/trips/{trip_id}/status")
async def get_trip_status(trip_id: str):
    """Получить актуальный статус поездки"""
    # Сначала проверяем кеш
    cached = await dispatcher.redis_client.get(f"trip:{trip_id}:status")
    if cached:
        return {"trip_id": trip_id, "status": cached.decode('utf-8'), "source": "cache"}
    
    # Если нет — идём в базу
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT id, status, updated_at FROM trips WHERE id = :trip_id"),
            {"trip_id": trip_id}
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Trip not found")
        
        return {"trip_id": row.id, "status": row.status, "updated_at": row.updated_at.isoformat()}