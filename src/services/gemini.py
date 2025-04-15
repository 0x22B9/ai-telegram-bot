import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions
import PIL.Image
import io

from src.config import config # Импортируем загруженную конфигурацию

# Настройка логгирования
logger = logging.getLogger(__name__)

# Конфигурация Gemini API при импорте модуля
if config and config.gemini.api_key:
    try:
        genai.configure(api_key=config.gemini.api_key)
        logger.info("Gemini API сконфигурирован.")
    except Exception as e:
        logger.error(f"Ошибка конфигурации Gemini API: {e}")
else:
    logger.warning("Ключ Gemini API не найден. Функциональность Gemini будет недоступна.")

# Настройки безопасности (можно настроить по необходимости)
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

ERROR_CODE_API_KEY = "ERROR_GEMINI_API_KEY"
ERROR_CODE_BLOCKED = "ERROR_BLOCKED_CONTENT"
ERROR_CODE_REQUEST_FAILED = "ERROR_GEMINI_REQUEST_FAILED"
ERROR_CODE_IMAGE_ANALYSIS_FAILED = "ERROR_IMAGE_ANALYSIS_FAILED"

async def generate_text(prompt: str) -> str | None:
    """
    Генерирует текст с использованием модели Gemini Pro.
    Возвращает сгенерированный текст, код ошибки или None.
    """
    if not (config and config.gemini.api_key):
        logger.error("Gemini API не сконфигурирован.")
        return "Ошибка: Ключ Gemini API не настроен." # Оставляем эту строку для явной проверки в хендлере

    try:
        model = genai.GenerativeModel('gemini-pro')
        response = await model.generate_content_async(prompt, safety_settings=safety_settings)

        if not response.parts:
             block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Неизвестно"
             logger.warning(f"Ответ от Gemini заблокирован. Причина: {block_reason}")
             # Возвращаем строку, которую легко проверить
             return f"Мой ответ был заблокирован из-за ограничений безопасности (Причина: {block_reason})."

        return response.text

    except Exception as e:
        logger.error(f"Ошибка при генерации текста Gemini: {e}", exc_info=True)
        # Возвращаем строку с ошибкой для проверки в хендлере
        return f"Произошла ошибка при обращении к Gemini: {e}"

async def analyze_image(image_bytes: bytes, prompt: str) -> str | None:
    """
    Анализирует изображение с использованием модели Gemini Pro Vision.
    Возвращает описание изображения, код ошибки или None.
    """
    if not (config and config.gemini.api_key):
        logger.error("Gemini API не сконфигурирован.")
        return "Ошибка: Ключ Gemini API не настроен."

    try:
        img = PIL.Image.open(io.BytesIO(image_bytes))
        model = genai.GenerativeModel('gemini-pro-vision')
        response = await model.generate_content_async([prompt, img], safety_settings=safety_settings)

        if not response.parts:
             block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Неизвестно"
             logger.warning(f"Ответ от Gemini (Vision) заблокирован. Причина: {block_reason}")
             # Возвращаем строку для проверки
             return f"Мой ответ на изображение был заблокирован из-за ограничений безопасности (Причина: {block_reason})."

        return response.text

    except Exception as e:
        logger.error(f"Ошибка при анализе изображения Gemini: {e}", exc_info=True)
        # Возвращаем строку для проверки
        return f"Произошла ошибка при анализе изображения: {e}"