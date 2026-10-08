"""
SearchFlightsAdapter — поиск рейсов через AirLabs API.

Два ключевых механизма:
1. /suggest — динамическое определение IATA-кода по названию города (любой город мира)
2. /routes  — статический справочник маршрутов между аэропортами
3. /flight  — live-данные конкретного рейса
"""
import os
from pathlib import Path

# Загрузка .env из корня проекта (на 2 уровня выше external_adapters/)
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

import hashlib
import httpx
from typing import List, Dict, Optional
from services.external_adapters.base import BaseAdapter
from shared.logger import get_logger

log = get_logger("search_flights")


# Обратный маппинг только для отображения (IATA → красивый город).
# НЕ используется для поиска — для этого есть /suggest.
IATA_TO_CITY = {
    "AER": "Sochi, RU", "SVO": "Moscow, RU", "DME": "Moscow, RU",
    "VKO": "Moscow, RU", "KZN": "Kazan, RU", "LED": "Saint Petersburg, RU",
    "KRR": "Krasnodar, RU", "UFA": "Ufa, RU", "SVX": "Yekaterinburg, RU",
    "OVB": "Novosibirsk, RU", "KUF": "Samara, RU", "GOJ": "Nizhny Novgorod, RU",
    "TJM": "Tyumen, RU", "ROV": "Rostov-on-Don, RU", "VOG": "Volgograd, RU",
    "PEE": "Perm, RU", "CEK": "Chelyabinsk, RU", "KGD": "Kaliningrad, RU",
    "VVO": "Vladivostok, RU", "KHV": "Khabarovsk, RU", "IKT": "Irkutsk, RU",
    "KJA": "Krasnoyarsk, RU", "OMS": "Omsk, RU",
    "LHR": "London, GB", "CDG": "Paris, FR", "BER": "Berlin, DE",
    "FCO": "Rome, IT", "MAD": "Madrid, ES", "AMS": "Amsterdam, NL",
    "IST": "Istanbul, TR", "DXB": "Dubai, AE", "PEK": "Beijing, CN",
    "PVG": "Shanghai, CN", "NRT": "Tokyo, JP", "ICN": "Seoul, KR",
    "JFK": "New York, US", "LAX": "Los Angeles, US", "SIN": "Singapore, SG",
    "BKK": "Bangkok, TH", "DEL": "Delhi, IN", "CAI": "Cairo, EG",
    "TLV": "Tel Aviv, IL", "ATH": "Athens, GR", "LIS": "Lisbon, PT",
    "BCN": "Barcelona, ES", "MXP": "Milan, IT", "VIE": "Vienna, AT",
    "ZRH": "Zurich, CH", "PRG": "Prague, CZ", "WAW": "Warsaw, PL",
    "HEL": "Helsinki, FI", "ARN": "Stockholm, SE", "OSL": "Oslo, NO",
    "CPH": "Copenhagen, DK", "SYD": "Sydney, AU", "YYZ": "Toronto, CA",
}


class SearchFlightsAdapter(BaseAdapter):
    name = "search_flights"
    BASE_URL = "https://airlabs.co/api/v9"

    def __init__(self):
        self.api_key = os.getenv("AIRLABS_KEY", "").strip()
        if not self.api_key:
            log.warning("AIRLABS_KEY не задан")

        # Кеши
        self._iata_cache: Dict[str, Optional[str]] = {}   # "samara" → "KUF"
        self._flights_cache: Dict[str, Dict] = {}         # "SU1001" → {...}

    async def health_check(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def iata_to_city(iata: str) -> Optional[str]:
        """'AER' → 'Sochi, RU'. Только для отображения."""
        if not iata:
            return None
        return IATA_TO_CITY.get(iata.upper())

    # ─────────────────────────────────────────────
    # Динамическое определение IATA через /suggest
    # ─────────────────────────────────────────────
    async def resolve_city_to_iata(self, city_name: str) -> Optional[str]:
        """
        Любой город мира → IATA-код.
        Использует AirLabs /suggest (city autocomplete).
        Результат кешируется в памяти.
        """
        if not self.api_key or not city_name:
            return None

        key = city_name.strip().lower()

        # Если это уже IATA-код (3 буквы) — возвращаем как есть
        if len(key) == 3 and key.isalpha():
            return key.upper()

        # Проверяем кеш
        if key in self._iata_cache:
            cached = self._iata_cache[key]
            log.info(f"resolve_city_to_iata: '{city_name}' из кеша → {cached}")
            return cached

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/suggest",
                    params={"q": city_name, "api_key": self.api_key},
                )
                resp.raise_for_status()
                data = resp.json()

                # Приоритет 1: города
                cities = data.get("cities") or []
                if cities:
                    iata = cities[0].get("city_code")
                    if iata:
                        self._iata_cache[key] = iata
                        log.info(f"resolve_city_to_iata: '{city_name}' → {iata} (city)")
                        return iata

                # Приоритет 2: аэропорты
                airports = data.get("airports") or []
                if airports:
                    iata = airports[0].get("iata_code")
                    if iata:
                        self._iata_cache[key] = iata
                        log.info(f"resolve_city_to_iata: '{city_name}' → {iata} (airport)")
                        return iata

                # Не нашли — кешируем None, чтобы не бить API лишний раз
                self._iata_cache[key] = None
                log.warning(f"resolve_city_to_iata: '{city_name}' не найден")
                return None

            except Exception as e:
                log.error(f"resolve_city_to_iata error: {e}")
                return None

    # ─────────────────────────────────────────────
    # Поиск рейсов через /routes
    # ─────────────────────────────────────────────
    async def search_flights(
        self, city_from: str, city_to: str, date: Optional[str] = None
    ) -> List[Dict]:
        """
        Ищет рейсы между двумя городами.
        Города могут быть названиями ('Samara') или IATA-кодами ('KUF').
        """
        if not self.api_key:
            log.warning("search_flights: AIRLABS_KEY не задан")
            return []

        # Динамическое определение IATA через /suggest
        dep_iata = await self.resolve_city_to_iata(city_from)
        arr_iata = await self.resolve_city_to_iata(city_to)

        if not dep_iata or not arr_iata:
            log.warning(f"Не могу определить IATA: {city_from} → {city_to}")
            return []

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/routes",
                    params={
                        "api_key": self.api_key,
                        "dep_iata": dep_iata,
                        "arr_iata": arr_iata,
                        "limit": 50,
                    },
                )
                resp.raise_for_status()
                routes = resp.json().get("response", [])

                if not routes:
                    log.info(f"search_flights: {dep_iata}→{arr_iata}, маршрутов нет")
                    return []

                flights: List[Dict] = []
                for r in routes:
                    flight_iata = r.get("flight_iata") or ""
                    if not flight_iata:
                        airline = r.get("airline_iata", "")
                        number = r.get("flight_number", "")
                        if airline and number:
                            flight_iata = f"{airline}{number}"
                    if not flight_iata:
                        continue

                    # Стабильный hash → цена и места
                    h = int(hashlib.md5(flight_iata.encode()).hexdigest()[:8], 16)
                    price = 12000 + (h % 5000)
                    seats = max(10, 20 - (h % 15))

                    flight = {
                        "flight_iata": flight_iata,
                        "airline": r.get("airline_iata", ""),
                        "dep_iata": dep_iata,
                        "arr_iata": arr_iata,
                        "dep_time": r.get("dep_time", ""),
                        "arr_time": r.get("arr_time", ""),
                        "duration": r.get("duration"),
                        "days": r.get("days", []),
                        "price_per_ticket": price,
                        "seats_left": seats,
                        "status": "SCHEDULED",
                    }
                    flights.append(flight)
                    # Сразу кешируем — понадобится при бронировании
                    self._flights_cache[flight_iata] = flight

                log.info(f"search_flights: {dep_iata}→{arr_iata}, найдено {len(flights)}")
                return flights

            except httpx.HTTPError as e:
                log.error(f"search_flights HTTP: {e}")
                return []
            except Exception as e:
                log.error(f"search_flights: {type(e).__name__}: {e}")
                return []

    # ─────────────────────────────────────────────
    # Данные по конкретному рейсу (для брони)
    # ─────────────────────────────────────────────
    async def get_flight_by_iata(self, flight_iata: str) -> Optional[Dict]:
        """
        Возвращает рейс по IATA.
        Приоритет: кеш из /routes → /flight API → None.
        """
        if not flight_iata:
            return None

        # 1. Кеш (данные из /routes — гарантированно валидны)
        if flight_iata in self._flights_cache:
            log.info(f"get_flight_by_iata: {flight_iata} из кеша")
            return self._flights_cache[flight_iata]

        # 2. Пробуем /flight API
        if not self.api_key:
            return None

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/flight",
                    params={"flight_iata": flight_iata, "api_key": self.api_key},
                )
                resp.raise_for_status()
                data = resp.json().get("response")
                if not data:
                    log.warning(f"get_flight_by_iata: {flight_iata} не найден")
                    return None

                h = int(hashlib.md5(flight_iata.encode()).hexdigest()[:8], 16)
                result = {
                    "flight_iata": data.get("flight_iata", flight_iata),
                    "dep_iata": data.get("dep_iata"),
                    "arr_iata": data.get("arr_iata"),
                    "dep_time": data.get("dep_time"),
                    "arr_time": data.get("arr_time"),
                    "duration": data.get("duration"),
                    "price_per_ticket": 12000 + (h % 5000),
                    "seats_left": max(10, 20 - (h % 15)),
                    "status": data.get("status", "scheduled").upper(),
                    "dep_terminal": data.get("dep_terminal"),
                    "dep_gate": data.get("dep_gate"),
                    "arr_terminal": data.get("arr_terminal"),
                }
                # Кешируем для будущих запросов
                self._flights_cache[flight_iata] = result
                return result
            except Exception as e:
                log.error(f"get_flight_by_iata: {e}")
                return None

