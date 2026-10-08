"""Точка входа Recommendation Service"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from services.recommendation_service.personalizer import personalizer
from shared.logger import get_logger

log = get_logger("recommendation_service")

class RankRequest(BaseModel):
    user_id: str
    hotels: List[dict]

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Recommendation Service starting...")
    yield

app = FastAPI(title="Recommendation Service", lifespan=lifespan)

@app.post("/rank")
async def rank(req: RankRequest):
    prefs = personalizer.get_user_prefs(req.user_id)
    ranked = personalizer.rank_hotels(req.hotels, prefs)
    return {"user_id": req.user_id, "ranked_hotels": ranked}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "recommendation_service"}
