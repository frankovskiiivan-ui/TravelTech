"""Адаптер для СБП / PayPal"""
import asyncio
from typing import Dict
from shared.logger import get_logger
from services.external_adapters.base import BaseAdapter

logger = get_logger("PaymentAPI")


class PaymentAPI(BaseAdapter):
    def __init__(self):
        super().__init__(base_url="https://api.payment.mock")

    async def process_payment(self, payment_data: Dict) -> Dict:
        logger.info(f"[Payment API] Processing {payment_data.get('method')} payment")
        await asyncio.sleep(0.7)
        return {
            "status": "success",
            "transaction_id": f"PAY-{payment_data.get('trip_id', 'unknown')}",
            "amount": payment_data.get("amount", 0)
        }