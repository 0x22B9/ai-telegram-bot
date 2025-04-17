# Импортируем роутеры из соответствующих модулей внутри пакета handlers
from .common import common_router
from .text import text_router
from .image import image_router # Роутер для обработки полученных фото
from .settings import settings_router
from .image_generation import image_generation_router # <<< ДОБАВИТЬ ЭТУ СТРОКУ ИМПОРТА

# Определяем, что будет экспортировано при 'from src.handlers import *'
# или что будет доступно через 'from src.handlers import ...'
__all__ = [
    "common_router",
    "text_router",
    "image_router",
    "settings_router",
    "image_generation_router", # <<< ДОБАВИТЬ ИМЯ РОУТЕРА СЮДА
]