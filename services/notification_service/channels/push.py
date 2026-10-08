from shared.logger import get_logger

log = get_logger("push_channel")


async def send(trip_id: str, message: str) -> bool:
    log.info(f"[PUSH] -> {trip_id}: {message}")
    return True
