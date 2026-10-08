"""Конфигурация проекта. Читает переменные из .env."""
import os
import shared.env_loader

def _load_env(path: str = ".env"):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()


class Settings:
    airlabs_key = os.getenv("AIRLABS_KEY", "")
    staying_key = os.getenv("STAYING_KEY", "")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    kafka_topic_notifications = "notifications"
    kafka_topic_trips = "trip-events"
    kafka_topic_feedback = "feedback"


settings = Settings()