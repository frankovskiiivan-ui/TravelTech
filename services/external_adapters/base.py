"""Базовый класс для всех адаптеров"""
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """Все внешние API адаптеры наследуются от этого класса"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url