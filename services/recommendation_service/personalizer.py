"""ML-модель персонализации текста уведомлений"""
from shared.logger import get_logger

logger = get_logger("RecommendationService")


class RecommendationService:
    """
    В продакшене здесь была бы реальная ML-модель (CatBoost, PyTorch).
    Для демо — простые правила.
    """
    
    async def personalize(self, user_id: str, text: str) -> str:
        logger.info(f"Personalizing for user={user_id}")
        
        # Простая "персонализация": добавляем эмодзи и обращение
        name = user_id.replace("user_", "User ")
        return f"{name}, {text} 🎯"