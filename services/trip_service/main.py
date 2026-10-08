"""Точка входа Trip Service"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.trip_service.dispatcher import dispatcher
from shared.database import db
from shared.cache import cache
from shared.kafka_client import kafka
from shared.config import settings
from shared.logger import get_logger

log = get_logger("trip_service")

class TripRequest(BaseModel):
    user_id: str
    flight_number: str
    city: Optional[str] = ""

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Trip Service starting...")
    await db.connect()
    await cache.connect()
    await kafka.start_producer()
    # Подписываемся на feedback
    await kafka.subscribe(settings.kafka_topic_feedback, "trip-service", dispatcher.handle_feedback)
    yield
    await kafka.stop_all()
    await cache.disconnect()
    await db.disconnect()

app = FastAPI(title="Trip Service", lifespan=lifespan)

@app.post("/trip/process")
async def process(req: TripRequest):
    try:
        return await dispatcher.process_request(req.user_id, req.flight_number, req.city)
    except Exception as e:
        log.error(f"Error: {e}")
        raise HTTPException(500, str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "service": "trip_service"}
