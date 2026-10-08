"""ML-персонализатор: ранжирование отелей по цене и рейтингу."""
from typing import Dict, List
from shared.logger import get_logger

log = get_logger("personalizer")


class RecommendationPersonalizer:
    def __init__(self):
        self.default_prefs = {
            "max_price": 250,
            "min_rating": 4.0,
            "weight_price": 0.4,
            "weight_rating": 0.6,
        }

    def get_user_prefs(self, user_id: str) -> dict:
        # Пока возвращаем дефолтные prefs для всех пользователей
        return self.default_prefs

    def rank_hotels(self, hotels: List[dict], user_prefs: Dict = None) -> List[dict]:
        prefs = user_prefs or self.default_prefs

        def score(h: dict) -> float:
            price = h.get("price", 0)
            rating = h.get("rating", 0)
            price_score = max(0.0, (prefs["max_price"] - price) / prefs["max_price"]) if prefs["max_price"] > 0 else 0
            rating_score = rating / 5.0
            return prefs["weight_price"] * price_score + prefs["weight_rating"] * rating_score

        ranked = sorted(hotels, key=score, reverse=True)
        log.info(f"Personalized {len(ranked)} hotels")
        return ranked


personalizer = RecommendationPersonalizer()
