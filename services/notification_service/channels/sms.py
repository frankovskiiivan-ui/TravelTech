"""SMS-уведомления"""
from shared.logger import get_logger

logger = get_logger("Channel.SMS")


async def send_sms(user_id: str, text: str) -> None:
    logger.info(f"📩 SMS → {user_id}: {text}")