import logging
import io
import asyncio
from PIL import Image
from huggingface_hub import InferenceClient
from huggingface_hub.utils import HfHubHTTPError
from requests.exceptions import Timeout as RequestsTimeout
try:
    from huggingface_hub.errors import InferenceTimeoutError
except ImportError:
    InferenceTimeoutError = None
from typing import Tuple, Optional

from src.config import config

logger = logging.getLogger(__name__)

IMAGE_GEN_SUCCESS = "IMAGE_GEN_SUCCESS"
IMAGE_GEN_API_ERROR = "IMAGE_GEN_API_ERROR"
IMAGE_GEN_TIMEOUT_ERROR = "IMAGE_GEN_TIMEOUT_ERROR"
IMAGE_GEN_RATE_LIMIT_ERROR = "IMAGE_GEN_RATE_LIMIT_ERROR"
IMAGE_GEN_CONTENT_FILTER_ERROR = "IMAGE_GEN_CONTENT_FILTER_ERROR"
IMAGE_GEN_UNKNOWN_ERROR = "IMAGE_GEN_UNKNOWN_ERROR"
IMAGE_GEN_CONNECTION_ERROR = "IMAGE_GEN_CONNECTION_ERROR"

hf_client: Optional[InferenceClient] = None
if config and config.hf and config.hf.api_token:
    try:
        hf_client = InferenceClient(token=config.hf.api_token, timeout=60)
        logger.info("Hugging Face InferenceClient initialized.")
    except Exception as e:
        logger.error(f"Cannot initialize Hugging Face InferenceClient: {e}")
else:
    logger.warning("Token for Hugging Face API not found. Image generation will not be available.")

async def generate_image_from_prompt(prompt: str) -> Tuple[Optional[bytes], str]:
    """
    Generates image with Hugging Face API by text prompt.
    Returns tuple (image_bytes | None, status_code).
    """
    if hf_client is None or not config:
        logger.error("Hugging Face client not configured for image generation or config not found.")
        return None, IMAGE_GEN_API_ERROR

    model_id = config.hf.image_gen_model_id
    logger.info(f"Requesting image generation with model '{model_id}'. Prompt: {prompt[:50]}...")

    try:
        loop = asyncio.get_running_loop()
        image: Image.Image = await loop.run_in_executor(
            None,
            lambda: hf_client.text_to_image(prompt, model=model_id)
        )

        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        logger.info(f"Image generation completed with model '{model_id}'. Prompt: {prompt[:50]}...")
        return img_byte_arr, IMAGE_GEN_SUCCESS

    except HfHubHTTPError as e:
        status_code = e.response.status_code
        error_message = str(e)
        error_details = e.response.text[:200] if e.response else "No response details"
        logger.error(f"HTTP error {status_code} from Hugging Face API ({model_id}): {error_message}. Details: {error_details}", exc_info=False)
        if status_code == 429:
            return None, IMAGE_GEN_RATE_LIMIT_ERROR
        elif status_code == 503 and "estimated_time" in error_message:
             return None, IMAGE_GEN_TIMEOUT_ERROR
        elif "safety checker" in error_message.lower() or "nsfw" in error_message.lower():
            return None, IMAGE_GEN_CONTENT_FILTER_ERROR
        else:
            return None, IMAGE_GEN_API_ERROR
    except (InferenceTimeoutError, RequestsTimeout) as e:
        logger.warning(f"Timeout error during image generation with model ({model_id}): {e}", exc_info=False)
        return None, IMAGE_GEN_TIMEOUT_ERROR
    except ConnectionError as e:
         logger.error(f"Connection error during image generation with model ({model_id}): {e}", exc_info=True)
         return None, IMAGE_GEN_CONNECTION_ERROR
    except Exception as e:
        logger.error(f"Unexpected error while generating image with model ({model_id}): {e}", exc_info=True)
        if "timeout" in str(e).lower():
             return None, IMAGE_GEN_TIMEOUT_ERROR
        return None, IMAGE_GEN_UNKNOWN_ERROR