"""Email-уведомления"""
from shared.logger import get_logger

logger = get_logger("Channel.Email")


async def send_email(user_id: str, text: str) -> None:
    logger.info(f"📧 EMAIL → {user_id}: {text}")