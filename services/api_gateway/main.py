"""Точка входа API Gateway"""
from fastapi import FastAPI
from shared.logger import get_logger
from services.api_gateway.routes import router

logger = get_logger("APIGateway")

app = FastAPI(
    title="TravelTech API Gateway",
    description="Точка входа для мобильного клиента",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    logger.info("🚀 API Gateway started")


@app.get("/health")
async def health():
    return {"status": "ok"}