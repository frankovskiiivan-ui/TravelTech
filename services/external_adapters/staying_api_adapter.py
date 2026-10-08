import shared.env_loader   # noqa: F401
import os
import json
import httpx
from datetime import datetime, timedelta
from services.external_adapters.base import BaseAdapter
from shared.logger import get_logger

log = get_logger("stayingapi")


class StayingAPIAdapter(BaseAdapter):
    name = "stayingapi"
    BASE_URL = "https://api.stayingapi.com/v1"

    def __init__(self):
        self.api_key = os.getenv("STAYING_KEY", "").strip()
        if not self.api_key:
            log.warning("STAYING_KEY не задан")
        self._cache: dict = {}

    async def health_check(self) -> bool:
        return bool(self.api_key)

    # ─────────────────────────────────────────────
    # Поиск отелей
    # ─────────────────────────────────────────────
    async def search_hotels(self, city: str, nights: int = 1) -> list:
        if not self.api_key or not city:
            return []

        cache_key = (city.strip().lower(), nights)
        if cache_key in self._cache:
            log.info(f"StayingAPI: {city} из кеша")
            return self._cache[cache_key]

        check_in = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=7 + max(nights, 1))).strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={
                        "location": city,
                        "checkIn": check_in,
                        "checkOut": check_out,
                        "adults": 2,
                        "platforms": "airbnb,booking",
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                raw = response.json()

                data = self._extract_data(raw)
                hotels = []
                for item in data[:5]:
                    hotel = self._parse_hotel(item, city, nights)
                    if hotel:
                        hotels.append(hotel)

                self._cache[cache_key] = hotels
                log.info(f"StayingAPI: {city}, найдено {len(hotels)} отелей")
                return hotels

            except httpx.HTTPStatusError as e:
                log.error(f"StayingAPI HTTP {e.response.status_code}: {e.response.text[:200]}")
                return []
            except Exception as e:
                log.error(f"StayingAPI error: {type(e).__name__}: {e}")
                return []

    @staticmethod
    def _extract_data(raw) -> list:
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            for key in ("data", "hotels", "results", "stays", "items"):
                value = raw.get(key)
                if isinstance(value, list):
                    return value
        return []

    # ─────────────────────────────────────────────
    # Парсинг одного отеля — РЕАЛЬНАЯ структура StayingAPI
    # ─────────────────────────────────────────────
    def _parse_hotel(self, item: dict, city: str, nights: int) -> dict | None:
        if not isinstance(item, dict):
            return None

        # ─── Цена: ВЛОЖЕННЫЙ объект item["price"] ───
        price_obj = item.get("price") or {}
        if not isinstance(price_obj, dict):
            price_obj = {}

        nightly = self._to_float(price_obj.get("nightlyPrice"))
        total = self._to_float(price_obj.get("totalPrice"))
        currency = price_obj.get("currency") or item.get("currency") or "EUR"

        # Если totalPrice не задан — считаем сами
        if total <= 0 and nightly > 0:
            total = nightly * nights

        # Пропускаем отели без цены
        if total <= 0 and nightly <= 0:
            log.warning(f"StayingAPI: пропущен отель без цены — {item.get('name', '?')}")
            return None

        # ─── Название: name есть в ответе! ───
        name = item.get("name") or item.get("title") or "Unknown hotel"

        # ─── Рейтинг: guestRating (не rating!) ───
        rating = self._to_float(item.get("guestRating"))
        rating_scale = self._to_float(item.get("ratingScale")) or 5.0

        # ─── Локация: вложенный location ───
        location = item.get("location") or {}
        actual_city = location.get("city") or city
        country = location.get("country") or ""

        # ─── ID и платформа ───
        listing_id = item.get("platformListingId") or item.get("id") or ""

        return {
            "hotel": name,
            "price": round(total, 2),
            "nightly_price": round(nightly, 2),
            "currency": currency,
            "rating": round(rating, 2),
            "rating_scale": rating_scale,
            "review_count": item.get("reviewCount") or 0,
            "nights": price_obj.get("nights") or nights,
            "city": city,
            "actual_city": actual_city,
            "country": country,
            "source": "StayingAPI",
            "platform": item.get("platform") or "",
            "url": item.get("url"),
            "listing_id": listing_id,
            "property_type": item.get("propertyType") or "",
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "max_occupancy": item.get("maxOccupancy"),
            "is_superhost": (item.get("host") or {}).get("isSuperhost", False),
            "host_name": (item.get("host") or {}).get("name"),
            "image": (item.get("images") or [None])[0],
        }

    @staticmethod
    def _to_float(value) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0