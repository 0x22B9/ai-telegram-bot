# Обновляем импорты, чтобы включить все роутеры
from .common import common_router
from .text import text_router
from .image import image_router

# Экспортируем все роутеры для удобного импорта в bot.py
__all__ = [
    "common_router",
    "text_router",
    "image_router",
]