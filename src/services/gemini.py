import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, ContentDict, GenerationConfigDict
from google.api_core import exceptions as api_core_exceptions
import PIL.Image
import io
from typing import List, Dict, Any, Optional

from src.config import config, VISION_MODEL, DEFAULT_TEXT_MODEL

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

GEMINI_QUOTA_ERROR = "GEMINI_QUOTA_ERROR"
GEMINI_API_KEY_ERROR = "GEMINI_API_KEY_ERROR"
GEMINI_BLOCKED_ERROR = "GEMINI_BLOCKED_ERROR"
GEMINI_REQUEST_ERROR = "GEMINI_REQUEST_ERROR"
IMAGE_ANALYSIS_ERROR = "IMAGE_ANALYSIS_ERROR"

async def generate_text_with_history(
    history: List[Dict[str, Any]],
    new_prompt: str,
    model_name: str = DEFAULT_TEXT_MODEL,
    # --- Добавлены параметры настроек ---
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None
    # ----------------------------------
) -> tuple[str | None, str | None]:
    if not (config and config.gemini.api_key):
        logger.error("Gemini API не сконфигурирован.")
        return None, GEMINI_API_KEY_ERROR

    try:
        logger.debug(f"Использование модели Gemini: {model_name}")
        model = genai.GenerativeModel(model_name)

        # --- Формируем GenerationConfig ---
        generation_config = GenerationConfigDict() # Используем типизированный dict
        config_params_set = False
        if temperature is not None:
            # Валидация (хотя должна быть и на уровне хендлера)
            if 0.0 <= temperature <= 1.0:
                 generation_config['temperature'] = temperature
                 config_params_set = True
            else:
                 logger.warning(f"Некорректное значение temperature ({temperature}), используется дефолтное API.")
        if max_output_tokens is not None:
             if max_output_tokens > 0:
                 generation_config['max_output_tokens'] = max_output_tokens
                 config_params_set = True
             else:
                 logger.warning(f"Некорректное значение max_output_tokens ({max_output_tokens}), используется дефолтное API.")

        logger.debug(f"Generation config: {generation_config if config_params_set else 'Default API settings'}")
        # ---------------------------------------

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
            generation_config=generation_config if config_params_set else None,
            safety_settings=safety_settings
        )

        if not response.parts:
             block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Неизвестно"
             logger.warning(f"Ответ от Gemini заблокирован (контекст). Причина: {block_reason}")
             return None, f"{GEMINI_BLOCKED_ERROR}:{block_reason}" # Передаем причину

        return response.text, None # Успех, возвращаем текст и None для ошибки

    except api_core_exceptions.ResourceExhausted as e: # Ловим ошибку 429 (квота)
        logger.error(f"Ошибка квоты Gemini ({model_name}): {e}", exc_info=False) # Полный трейсбек не нужен
        return None, GEMINI_QUOTA_ERROR # Возвращаем новый код ошибки
    except Exception as e: # Ловим остальные ошибки
        # Добавим проверку, содержит ли текст ошибки '429' на всякий случай,
        # если исключение было другим, но содержало этот код.
        if "429" in str(e) and "quota" in str(e).lower():
             logger.error(f"Обнаружена ошибка, похожая на квоту, в общем Exception ({model_name}): {e}", exc_info=False)
             return None, GEMINI_QUOTA_ERROR
        else:
             logger.error(f"Ошибка при генерации текста Gemini ({model_name}): {e}", exc_info=True)
             # Передаем текст ошибки для диагностики
             return None, f"{GEMINI_REQUEST_ERROR}:{e}"

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
        model = genai.GenerativeModel(VISION_MODEL)
        response = await model.generate_content_async([prompt, img], safety_settings=safety_settings)

        if not response.parts:
             block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Неизвестно"
             logger.warning(f"Ответ от Gemini ({VISION_MODEL}) заблокирован. Причина: {block_reason}")
             return None, f"{GEMINI_BLOCKED_ERROR}:{block_reason}"

        return response.text

    except api_core_exceptions.ResourceExhausted as e: # Ловим ошибку 429 (квота)
        logger.error(f"Ошибка квоты Gemini Vision ({VISION_MODEL}): {e}", exc_info=False)
        return None, GEMINI_QUOTA_ERROR
    except Exception as e: # Ловим остальные ошибки
        if "429" in str(e) and "quota" in str(e).lower():
             logger.error(f"Обнаружена ошибка, похожая на квоту, в общем Exception ({VISION_MODEL}): {e}", exc_info=False)
             return None, GEMINI_QUOTA_ERROR
        else:
             logger.error(f"Ошибка при анализе изображения Gemini ({VISION_MODEL}): {e}", exc_info=True)
             return None, f"{IMAGE_ANALYSIS_ERROR}:{e}"