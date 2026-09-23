"""Push-уведомления"""
from shared.logger import get_logger

logger = get_logger("Channel.Push")


async def send_push(user_id: str, text: str) -> None:
    logger.info(f"📱 PUSH → {user_id}: {text}")