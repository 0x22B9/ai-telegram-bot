import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, ContentDict, PartDict
import PIL.Image
import io
from typing import List, Dict, Any # Добавлено для типизации

from src.config import config

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

GEMINI_API_KEY_ERROR = "GEMINI_API_KEY_ERROR"
GEMINI_BLOCKED_ERROR = "GEMINI_BLOCKED_ERROR"
GEMINI_REQUEST_ERROR = "GEMINI_REQUEST_ERROR"
IMAGE_ANALYSIS_ERROR = "IMAGE_ANALYSIS_ERROR"

async def generate_text_with_history(history: List[Dict[str, Any]], new_prompt: str) -> tuple[str | None, str | None]:
    """
    Генерирует текст с использованием модели Gemini Pro, учитывая историю чата.
    Возвращает кортеж: (сгенерированный_текст | None, код_ошибки | None).
    """
    if not (config and config.gemini.api_key):
        logger.error("Gemini API не сконфигурирован.")
        return None, GEMINI_API_KEY_ERROR

    try:
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')

        # Важно: Конвертируем наш формат истории в формат, ожидаемый библиотекой google-generativeai
        # Наш формат: [{"role": "user", "parts": [{"text": "..."}]}, ...]
        # Он должен быть совместим с ContentDict
        typed_history: List[ContentDict] = []
        for msg in history:
            # Простая проверка типов для надежности
            if isinstance(msg, dict) and "role" in msg and "parts" in msg:
                typed_history.append(msg) # Добавляем как есть, если формат совпадает
            else:
                logger.warning(f"Некорректный формат сообщения в истории: {msg}")


        chat = model.start_chat(history=typed_history)

        response = await chat.send_message_async(
            new_prompt,
            safety_settings=safety_settings
        )

        if not response.parts:
             block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Неизвестно"
             logger.warning(f"Ответ от Gemini заблокирован (контекст). Причина: {block_reason}")
             return None, f"{GEMINI_BLOCKED_ERROR}:{block_reason}" # Передаем причину

        return response.text, None # Успех, возвращаем текст и None для ошибки

    except Exception as e:
        logger.error(f"Ошибка при генерации текста Gemini (с историей): {e}", exc_info=True)
        return None, f"{GEMINI_REQUEST_ERROR}:{e}" # Передаем текст ошибки

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
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
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