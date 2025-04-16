# src/handlers/__init__.py

# Импортируем роутеры из соответствующих модулей
from .common import common_router
from .text import text_router
from .image import image_router
from .settings import settings_router # <<< ДОБАВИТЬ ЭТОТ ИМПОРТ

# Определяем, что будет экспортировано при импорте "from src.handlers import *"
# или что будет доступно при "from src.handlers import ..."
__all__ = [
    "common_router",
    "text_router",
    "image_router",
    "settings_router", # <<< ДОБАВИТЬ ИМЯ СЮДА
]