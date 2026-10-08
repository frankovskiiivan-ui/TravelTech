from shared.logger import get_logger

log = get_logger("email_channel")


async def send(trip_id: str, message: str) -> bool:
    log.info(f"[EMAIL] -> {trip_id}: {message}")
    return True
