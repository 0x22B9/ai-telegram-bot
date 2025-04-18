from .common import common_router
from .text import text_router
from .image import image_router
from .settings import settings_router
from .image_generation import image_generation_router
from .audio import audio_router
from .document import document_router
from .privacy import privacy_router # <<< ДОБАВИТЬ ИМПОРТ

__all__ = [
    "common_router",
    "text_router",
    "image_router",
    "settings_router",
    "image_generation_router",
    "audio_router",
    "document_router",
    "privacy_router", # <<< ДОБАВИТЬ В ЭКСПОРТ
]