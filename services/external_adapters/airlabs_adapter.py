import os
import httpx
import re
from services.external_adapters.base import BaseAdapter
from shared.logger import get_logger

log = get_logger("airlabs")


# IATA-коды аэропортов → город для поиска отелей
IATA_TO_CITY = {
    "AER": "Sochi, RU",
    "SVO": "Moscow, RU",
    "DME": "Moscow, RU",
    "VKO": "Moscow, RU",
    "KZN": "Kazan, RU",
    "LED": "Saint Petersburg, RU",
    "KRR": "Krasnodar, RU",
    "MRV": "Mineralnye Vody, RU",
    "NBC": "Nizhnekamsk, RU",
    "UFA": "Ufa, RU",
    "EGO": "Belgorod, RU",
    "VOZ": "Voronezh, RU",
    "GOJ": "Nizhny Novgorod, RU",
    "SVX": "Yekaterinburg, RU",
    "OVB": "Novosibirsk, RU",
    "KRR": "Krasnodar, RU",
    "AER": "Sochi, RU",
    "REN": "Samara, RU",
    "KUF": "Samara, RU",
}


class AirLabsAdapter(BaseAdapter):
    name = "airlabs"
    BASE_URL = "https://airlabs.co/api/v9"

    def __init__(self):
        self.api_key = os.getenv("AIRLABS_KEY", "").strip()
        if not self.api_key:
            log.warning("AIRLABS_KEY не задан")

    async def health_check(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def iata_to_city(iata_code: str) -> str | None:
        """Возвращает город по IATA-коду аэропорта."""
        if not iata_code:
            return None
        return IATA_TO_CITY.get(iata_code.upper())

    async def get_flight_status(self, flight_number: str) -> dict:
        clean = flight_number.strip().upper().replace(" ", "").replace("-", "")
        if not re.match(r"^[A-Z0-9]{2,3}\d{1,4}$", clean):
            log.error(f"Неверный формат номера рейса: {flight_number}")
            return {"status": "INVALID_FORMAT", "source": "AirLabs"}

        if not self.api_key:
            return {"status": "NO_API_KEY", "source": "AirLabs"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/flight",
                    params={"flight_iata": clean, "api_key": self.api_key}
                )
                data = response.json().get("response")

                if not data:
                    log.warning(f"AirLabs: рейс {clean} не найден")
                    return {"status": "NOT_FOUND", "source": "AirLabs"}

                raw_status = data.get("status", "").lower()
                status_map = {
                    "scheduled": "ON_TIME",
                    "en-route": "ON_TIME",
                    "landed": "ON_TIME",
                    "cancelled": "CANCELLED",
                    "delayed": "DELAYED",
                    "diverted": "DELAYED",
                }

                delay = int(data.get("dep_delayed", 0) or 0)
                final_status = "DELAYED" if delay > 15 else status_map.get(raw_status, "UNKNOWN")

                # IATA-коды аэропортов вылета и прилёта
                dep_iata = data.get("dep_iata")
                arr_iata = data.get("arr_iata")

                return {
                    "flight": data.get("flight_iata"),
                    "status": final_status,
                    "delay_minutes": delay,
                    "departure_terminal": data.get("dep_terminal"),
                    "departure_gate": data.get("dep_gate"),
                    "dep_iata": dep_iata,
                    "arr_iata": arr_iata,
                    "arr_city": self.iata_to_city(arr_iata),
                    "source": "AirLabs"
                }
            except Exception as e:
                log.error(f"AirLabs error: {e}")
                return {"status": "API_ERROR", "source": "AirLabs"}
