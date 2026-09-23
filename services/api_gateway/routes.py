"""Эндпоинты API Gateway"""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from shared.config import settings
from shared.logger import get_logger

logger = get_logger("APIGateway.Routes")
router = APIRouter()


# --- Pydantic-схемы запросов ---
class FlightStatusRequest(BaseModel):
    flight_number: str

class SearchRequest(BaseModel):
    user_id: str
    origin: str
    destination: str
    date: str | None = None

class PaymentRequest(BaseModel):
    user_id: str
    trip_id: str
    amount: float
    method: str  # SBP, PayPal


# --- Эндпоинты ---

@router.post("/status")
async def get_flight_status(req: FlightStatusRequest):
    """Узнать статус рейса"""
    logger.info(f"POST /status flight={req.flight_number}")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.TRIP_SERVICE_URL}/internal/status",
                json={"flight_number": req.flight_number},
                timeout=10.0
            )
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Trip service unavailable: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable")


@router.post("/search")
async def search_trip(req: SearchRequest):
    """Найти альтернативный вариант"""
    logger.info(f"POST /search user={req.user_id}")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.TRIP_SERVICE_URL}/internal/search",
                json=req.model_dump(),
                timeout=30.0
            )
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Trip service unavailable: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable")


@router.post("/pay")
async def pay(req: PaymentRequest):
    """Оплатить поездку"""
    logger.info(f"POST /pay trip={req.trip_id}")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.TRIP_SERVICE_URL}/internal/pay",
                json=req.model_dump(),
                timeout=30.0
            )
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Trip service unavailable: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable")