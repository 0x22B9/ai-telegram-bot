import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, ContentDict, GenerationConfigDict
from google.api_core import exceptions as api_core_exceptions
import PIL.Image
import io
from typing import List, Dict, Any, Optional, Tuple

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

AUDIO_TRANSCRIPTION_MODEL = "gemini-2.0-flash"

GEMINI_QUOTA_ERROR = "GEMINI_QUOTA_ERROR"
GEMINI_API_KEY_ERROR = "GEMINI_API_KEY_ERROR"
GEMINI_BLOCKED_ERROR = "GEMINI_BLOCKED_ERROR"
GEMINI_REQUEST_ERROR = "GEMINI_REQUEST_ERROR"
IMAGE_ANALYSIS_ERROR = "IMAGE_ANALYSIS_ERROR"
GEMINI_TRANSCRIPTION_ERROR = "GEMINI_TRANSCRIPTION_ERROR"

async def transcribe_audio(audio_bytes: bytes, mime_type: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Транскрибирует аудиофайл с использованием Gemini API.
    Возвращает (transcribed_text | None, error_code | None).
    """
    if not (config and config.gemini.api_key):
        logger.error("Gemini API не сконфигурирован для транскрипции.")
        return None, GEMINI_API_KEY_ERROR

    transcription_prompt = "Transcribe this audio." # Простой промпт для транскрипции

    try:
        logger.info(f"Загрузка аудио ({len(audio_bytes)} байт) в Gemini...")
        # 1. Загружаем файл
        # Создаем файлоподобный объект из байтов
        audio_file_obj = io.BytesIO(audio_bytes)
        # mime_type важен для корректной обработки файла API
        # Используем аргумент 'path' для передачи BytesIO
        audio_file = genai.upload_file(
            path=audio_file_obj, # <<< ПРАВИЛЬНЫЙ АРГУМЕНТ: path
            display_name="user_voice_message.ogg", # Имя файла (даем расширение для ясности)
            mime_type=mime_type
        )
        # audio_file_obj закроется автоматически при сборке мусора.
        logger.info(f"Аудио успешно загружено: {audio_file.name}")

        # 2. Генерируем контент с использованием загруженного файла
        logger.info(f"Запрос транскрипции моделью {AUDIO_TRANSCRIPTION_MODEL}...")
        model = genai.GenerativeModel(AUDIO_TRANSCRIPTION_MODEL)
        response = await model.generate_content_async(
            [transcription_prompt, audio_file], # Передаем промпт и файл
            safety_settings=safety_settings,
            # GenerationConfig для транскрипции обычно не нужен, но можно указать
            # generation_config={"temperature": 0.1} # Низкая температура для точности
        )

        if not response.parts:
            block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Неизвестно"
            logger.warning(f"Транскрипция Gemini ({AUDIO_TRANSCRIPTION_MODEL}) заблокирована. Причина: {block_reason}")
            # Не удаляем файл при блокировке, он может быть полезен для анализа
            # genai.delete_file(audio_file.name) # Удаляем файл после использования
            return None, f"{GEMINI_BLOCKED_ERROR}:{block_reason}"

        transcribed_text = response.text
        logger.info(f"Аудио успешно транскрибировано ({len(transcribed_text)} символов).")

        # 3. Удаляем файл после успешного использования (рекомендуется)
        try:
            genai.delete_file(audio_file.name)
            logger.info(f"Загруженный аудиофайл {audio_file.name} удален.")
        except Exception as delete_err:
            logger.warning(f"Не удалось удалить загруженный аудиофайл {audio_file.name}: {delete_err}")


        return transcribed_text, None

    except api_core_exceptions.ResourceExhausted as e:
        logger.error(f"Ошибка квоты Gemini при транскрипции ({AUDIO_TRANSCRIPTION_MODEL}): {e}", exc_info=False)
        # Попытка удалить файл, если он был загружен до ошибки квоты
        if 'audio_file' in locals() and audio_file:
             try: genai.delete_file(audio_file.name)
             except Exception: pass
        return None, GEMINI_QUOTA_ERROR
    except Exception as e:
        logger.error(f"Ошибка при транскрипции аудио Gemini ({AUDIO_TRANSCRIPTION_MODEL}): {e}", exc_info=True)
        # Попытка удалить файл, если он был загружен до ошибки
        if 'audio_file' in locals() and audio_file:
             try: genai.delete_file(audio_file.name)
             except Exception: pass

        # Возвращаем специфичную ошибку транскрипции
        return None, f"{GEMINI_TRANSCRIPTION_ERROR}:{e}"

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