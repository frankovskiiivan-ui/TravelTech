from shared.logger import get_logger

log = get_logger("sms_channel")


async def send(trip_id: str, message: str) -> bool:
    log.info(f"[SMS] -> {trip_id}: {message}")
    return True
