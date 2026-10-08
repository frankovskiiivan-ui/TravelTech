"""Notification Handler — рассылает уведомления по каналам."""
from typing import Callable, Dict
from shared.logger import get_logger
from shared.database import db
from services.notification_service.channels import push, email, sms

log = get_logger("notification_handler")

CHANNEL_MAP: Dict[str, Callable] = {
    "push": push.send,
    "email": email.send,
    "sms": sms.send,
}


class NotificationHandler:
    async def handle(self, message: dict):
        trip_id = message.get("trip_id")
        text = message.get("message", "")
        channels = message.get("channels", ["push"])

        log.info(f"Notification for {trip_id}: channels={channels}")

        for ch in channels:
            sender = CHANNEL_MAP.get(ch)
            if sender:
                try:
                    await sender(trip_id, text)
                    try:
                        await db.save_notification(trip_id, text, ch)
                    except NotImplementedError:
                        pass
                except Exception as e:
                    log.error(f"Channel {ch} failed: {e}")


handler = NotificationHandler()
