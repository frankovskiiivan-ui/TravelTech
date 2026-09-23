"""Настройки проекта (читаются из переменных окружения)"""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Database
    POSTGRES_DSN: str = os.getenv("POSTGRES_DSN", "postgresql://user:pass@localhost:5432/traveltech")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Kafka
    KAFKA_BOOTSTRAP: str = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
    KAFKA_TOPIC_EVENTS: str = "trip_events"
    
    # External API
    AVIATION_API_URL: str = os.getenv("AVIATION_API_URL", "https://api.aviation.mock")
    BOOKING_API_URL: str = os.getenv("BOOKING_API_URL", "https://api.booking.mock")
    PAYMENT_API_URL: str = os.getenv("PAYMENT_API_URL", "https://api.payment.mock")
    
    # Service URLs
    TRIP_SERVICE_URL: str = os.getenv("TRIP_SERVICE_URL", "http://trip_service:8001")
    FLIGHT_TRACKER_URL: str = os.getenv("FLIGHT_TRACKER_URL", "http://flight_tracker:8002")


settings = Settings()