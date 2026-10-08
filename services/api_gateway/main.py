"""
API Gateway — точка входа.
Все сервисы работают в одном процессе через Mock-инфраструктуру.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional

# ---- Подмена инфраструктуры на Mock ----
import shared.database as db_mod
import shared.cache as cache_mod
import shared.kafka_client as kafka_mod
from shared.mocks import MockDatabase, MockCache, MockKafka

db_mod.db = MockDatabase()
cache_mod.cache = MockCache()
kafka_mod.kafka = MockKafka()

# ---- Подмена зависимостей в сервисах ----
import services.trip_service.dispatcher as disp_mod
disp_mod.db = db_mod.db
disp_mod.cache = cache_mod.cache
disp_mod.kafka = kafka_mod.kafka

import services.notification_service.handler as handler_mod
handler_mod.db = db_mod.db

from services.trip_service.dispatcher import TripServiceDispatcher
from services.notification_service.handler import NotificationHandler


dispatcher = TripServiceDispatcher()
notif_handler = NotificationHandler()


# ---- Схемы ----
class SearchRequest(BaseModel):
    city_from: str
    city_to: str
    date: Optional[str] = None


class BookRequest(BaseModel):
    user_id: str
    flight_iata: str
    passengers: int = Field(ge=1, le=9)


class FeedbackRequest(BaseModel):
    trip_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = ""


# ---- Lifespan ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    await kafka_mod.kafka.subscribe("notifications", "notif-svc", notif_handler.handle)
    await kafka_mod.kafka.subscribe("feedback", "trip-svc", dispatcher.handle_feedback)
    print("=" * 60)
    print("TravelTech API Gateway запущен")
    print("   AIRLABS_KEY:", "OK" if os.getenv("AIRLABS_KEY") else "ОТСУТСТВУЕТ")
    print("   STAYING_KEY:", "OK" if os.getenv("STAYING_KEY") else "ОТСУТСТВУЕТ")
    print("=" * 60)
    yield
    print("Остановлен")


app = FastAPI(title="TravelTech API Gateway", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ---- API ----
@app.post("/api/search-flights")
async def api_search_flights(req: SearchRequest):
    flights = await dispatcher.search_flights(req.city_from, req.city_to, req.date)
    return {"flights": flights}


@app.post("/api/book-trip")
async def api_book_trip(req: BookRequest):
    result = await dispatcher.book_trip(req.user_id, req.flight_iata, req.passengers)
    if result.get("status") in ("ERROR", "FLIGHT_NOT_FOUND", "NO_SEATS"):
        raise HTTPException(400, result.get("message", "Ошибка бронирования"))
    return result


@app.post("/api/feedback")
async def api_feedback(req: FeedbackRequest):
    await kafka_mod.kafka.publish("feedback", req.model_dump())
    return {"status": "ok", "message": "Спасибо за отзыв!"}


@app.get("/api/trips")
async def api_trips():
    return await db_mod.db.get_all_trips()


@app.get("/api/stats")
async def api_stats():
    return await db_mod.db.get_stats()


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---- Frontend ----
frontend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(frontend_path, "index.html"))
