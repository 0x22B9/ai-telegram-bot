import logging
import io
from PIL import Image
from huggingface_hub import InferenceClient
from huggingface_hub.utils import HfHubHTTPError # <<< Импортируем HfHubHTTPError из подмодуля utils
from typing import Tuple, Optional

from src.config import config # Импортируем общую конфигурацию

logger = logging.getLogger(__name__)

# Коды ошибок для генерации изображений
IMAGE_GEN_SUCCESS = "IMAGE_GEN_SUCCESS"
IMAGE_GEN_API_ERROR = "IMAGE_GEN_API_ERROR"
IMAGE_GEN_TIMEOUT_ERROR = "IMAGE_GEN_TIMEOUT_ERROR" # Обычно часть API_ERROR
IMAGE_GEN_RATE_LIMIT_ERROR = "IMAGE_GEN_RATE_LIMIT_ERROR"
IMAGE_GEN_CONTENT_FILTER_ERROR = "IMAGE_GEN_CONTENT_FILTER_ERROR" # Если модель такое возвращает
IMAGE_GEN_UNKNOWN_ERROR = "IMAGE_GEN_UNKNOWN_ERROR"

# Инициализация клиента при загрузке модуля (если токен есть)
hf_client: Optional[InferenceClient] = None
if config and config.hf and config.hf.api_token:
    try:
        hf_client = InferenceClient(token=config.hf.api_token)
        logger.info("Hugging Face InferenceClient инициализирован.")
    except Exception as e:
        logger.error(f"Не удалось инициализировать Hugging Face InferenceClient: {e}")
else:
    logger.warning("Токен Hugging Face API не найден. Генерация изображений будет недоступна.")

async def generate_image_from_prompt(prompt: str) -> Tuple[Optional[bytes], str]:
    """
    Генерирует изображение по текстовому промпту с использованием Hugging Face API.
    Возвращает кортеж: (image_bytes | None, status_code).
    """
    if hf_client is None or not config:
        logger.error("Hugging Face клиент не инициализирован или конфигурация отсутствует.")
        return None, IMAGE_GEN_API_ERROR

    model_id = config.hf.image_gen_model_id
    logger.info(f"Запрос на генерацию изображения моделью '{model_id}' с промптом: {prompt[:50]}...")

    try:
        # Вызов API (может занять время, выполняется синхронно библиотекой,
        # но мы вызываем из async функции, aiogram это обработает)
        # Важно: Использовать await нельзя, т.к. client.text_to_image синхронный
        image: Image.Image = hf_client.text_to_image(prompt, model=model_id)

        # Конвертация PIL Image в байты
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG') # Сохраняем в PNG
        img_byte_arr = img_byte_arr.getvalue()

        logger.info(f"Изображение успешно сгенерировано для промпта: {prompt[:50]}...")
        return img_byte_arr, IMAGE_GEN_SUCCESS

    except HfHubHTTPError as e:
        # Обрабатываем специфичные ошибки HF API
        status_code = e.response.status_code
        error_message = str(e)
        logger.error(f"Ошибка HTTP {status_code} от Hugging Face API ({model_id}): {error_message}", exc_info=False)
        if status_code == 429: # Too Many Requests
            return None, IMAGE_GEN_RATE_LIMIT_ERROR
        elif status_code == 503 and "estimated_time" in error_message: # Model loading or unavailable
            # Можно вернуть как таймаут или специфичную ошибку загрузки модели
             return None, IMAGE_GEN_TIMEOUT_ERROR # Или создать IMAGE_GEN_MODEL_LOADING_ERROR
        elif "safety checker" in error_message.lower() or "nsfw" in error_message.lower():
            return None, IMAGE_GEN_CONTENT_FILTER_ERROR
        else:
            return None, IMAGE_GEN_API_ERROR # Общая ошибка API

    except Exception as e: # Ловим другие возможные ошибки
        logger.error(f"Неожиданная ошибка при генерации изображения ({model_id}): {e}", exc_info=True)
        # Проверяем на таймаут, если он не был пойман как HfHubHTTPError
        if "timeout" in str(e).lower():
             return None, IMAGE_GEN_TIMEOUT_ERROR
        return None, IMAGE_GEN_UNKNOWN_ERROR