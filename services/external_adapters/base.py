"""Базовый класс для всех адаптеров"""
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def health_check(self) -> bool: ...
