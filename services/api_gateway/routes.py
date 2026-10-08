"""Эндпоинты API Gateway"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import uuid
from shared.logger import get_logger
from shared.database import db
from shared.kafka_client import kafka
from shared.config import settings

log = get_logger("api_gateway")
router = APIRouter(prefix="/api", tags=["gateway"])

# --- Схемы ---
class TripRequest(BaseModel):
    user_id: str
    flight_number: str
    city: str

class FeedbackRequest(BaseModel):
    trip_id: str
    rating: int
    comment: Optional[str] = ""

# --- Endpoints ---

@router.post("/check-flight")
async def check_flight(req: TripRequest):
    """Проксирует запрос в Trip Service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{settings.trip_service_url}/trip/process",
                json=req.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.error(f"Trip Service error: {e}")
            raise HTTPException(status_code=502, detail="Trip service unavailable")

@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Отправляет feedback в Kafka"""
    await kafka.publish(settings.kafka_topic_feedback, req.model_dump())
    return {"status": "ok", "message": "Спасибо за отзыв!"}

@router.get("/trips")
async def get_trips():
    return await db.get_all_trips()

@router.get("/trip/{trip_id}")
async def get_trip(trip_id: str):
    trip = await db.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@router.get("/stats")
async def get_stats():
    return await db.get_stats()