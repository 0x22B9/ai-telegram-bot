import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, ContentDict, GenerationConfigDict
from google.api_core import exceptions as api_core_exceptions
import PIL.Image
import io
from typing import List, Dict, Any, Optional, Tuple

from src.config import config, VISION_MODEL, DEFAULT_TEXT_MODEL

logger = logging.getLogger(__name__)

if config and config.gemini.api_key:
    try:
        genai.configure(api_key=config.gemini.api_key)
        logger.info("Gemini API configured.")
    except Exception as e:
        logger.error(f"Gemini API configuration error: {e}")
else:
    logger.warning("Gemini API Key not found. Gemini API will not be available.")

safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

AUDIO_TRANSCRIPTION_MODEL = "gemini-2.5-flash-preview-04-17"

GEMINI_QUOTA_ERROR = "GEMINI_QUOTA_ERROR"
GEMINI_API_KEY_ERROR = "GEMINI_API_KEY_ERROR"
GEMINI_BLOCKED_ERROR = "GEMINI_BLOCKED_ERROR"
GEMINI_REQUEST_ERROR = "GEMINI_REQUEST_ERROR"
IMAGE_ANALYSIS_ERROR = "IMAGE_ANALYSIS_ERROR"
GEMINI_TRANSCRIPTION_ERROR = "GEMINI_TRANSCRIPTION_ERROR"
GEMINI_API_KEY_INVALID = "GEMINI_API_KEY_INVALID"
GEMINI_SERVICE_UNAVAILABLE = "GEMINI_SERVICE_UNAVAILABLE"
GEMINI_UNKNOWN_API_ERROR = "GEMINI_UNKNOWN_API_ERROR"

async def transcribe_audio(audio_bytes: bytes, mime_type: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Transcribes audio with Gemini API.
    Returns (transcribed_text | None, error_code | None).
    """
    if not (config and config.gemini.api_key):
        logger.error("Gemini API not configured for transcription.")
        return None, GEMINI_API_KEY_ERROR

    transcription_prompt = "Transcribe this audio."

    try:
        logger.info(f"Loading audio ({len(audio_bytes)} byte) in Gemini...")
        audio_file_obj = io.BytesIO(audio_bytes)
        audio_file = genai.upload_file(
            path=audio_file_obj,
            display_name="user_voice_message.ogg",
            mime_type=mime_type
        )
        logger.info(f"Audio successfully loaded in Gemini: {audio_file.name}")

        logger.info(f"Requesting transcription with model {AUDIO_TRANSCRIPTION_MODEL}...")
        model = genai.GenerativeModel(AUDIO_TRANSCRIPTION_MODEL)
        response = await model.generate_content_async(
            [transcription_prompt, audio_file],
            safety_settings=safety_settings,
        )

        if not response.parts:
            block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Unknown reason."
            logger.warning(f"Transcribe from Gemini ({AUDIO_TRANSCRIPTION_MODEL}) blocked. Reason: {block_reason}")
            return None, f"{GEMINI_BLOCKED_ERROR}:{block_reason}"

        transcribed_text = response.text
        logger.info(f"Audio succesfully transcribed ({len(transcribed_text)} symbols).")
        return transcribed_text, None

    except api_core_exceptions.PermissionDenied as e:
        logger.error(f"Permission denied during audio transcription ({AUDIO_TRANSCRIPTION_MODEL}). Invalid API Key? Error: {e}", exc_info=False)
        return None, GEMINI_API_KEY_INVALID
    except api_core_exceptions.ResourceExhausted as e:
        logger.error(f"Quota exceeded while transcribing audio ({AUDIO_TRANSCRIPTION_MODEL}): {e}", exc_info=False)
        return None, GEMINI_QUOTA_ERROR
    except api_core_exceptions.ServiceUnavailable as e:
        logger.warning(f"Service unavailable during audio transcription ({AUDIO_TRANSCRIPTION_MODEL}): {e}", exc_info=False)
        return None, GEMINI_SERVICE_UNAVAILABLE
    except api_core_exceptions.GoogleAPIError as e:
        logger.error(f"Google API error during audio transcription ({AUDIO_TRANSCRIPTION_MODEL}): {e}", exc_info=True)
        return None, f"{GEMINI_UNKNOWN_API_ERROR}:{type(e).__name__}"
    except Exception as e:
        logger.error(f"Unexpected error transcribing audio ({AUDIO_TRANSCRIPTION_MODEL}): {e}", exc_info=True)
        return None, f"{GEMINI_TRANSCRIPTION_ERROR}:{type(e).__name__}"
    finally:
        if 'audio_file' in locals() and audio_file:
            try:
                genai.delete_file(audio_file.name)
                logger.info(f"Uploaded audio file {audio_file.name} deleted in finally block.")
            except Exception as delete_err:
                logger.warning(f"Could not delete audio file {audio_file.name} in finally block: {delete_err}")


async def generate_text_with_history(
    history: List[Dict[str, Any]],
    new_prompt: str,
    model_name: str = DEFAULT_TEXT_MODEL,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None
) -> tuple[str | None, str | None]:
    if not (config and config.gemini.api_key):
        logger.error("Gemini API is not configured.")
        return None, GEMINI_API_KEY_ERROR

    try:
        logger.debug(f"Using Gemini model: {model_name}")
        model = genai.GenerativeModel(model_name)

        generation_config = GenerationConfigDict()
        config_params_set = False
        if temperature is not None:
            if 0.0 <= temperature <= 1.0:
                generation_config['temperature'] = temperature
                config_params_set = True
            else:
                logger.warning(f"Incorrect value for temperature ({temperature}), using default value from API.")
        if max_output_tokens is not None:
             if max_output_tokens > 0:
                generation_config['max_output_tokens'] = max_output_tokens
                config_params_set = True
             else:
                logger.warning(f"Incorrect value for max_output_tokens ({max_output_tokens}), using default value from API.")

        logger.debug(f"Generation config: {generation_config if config_params_set else 'Default API settings'}")

        typed_history: List[ContentDict] = []
        for msg in history:
            if isinstance(msg, dict) and "role" in msg and "parts" in msg:
                typed_history.append(msg)
            else:
                logger.warning(f"Incorrect format for history message: {msg}")


        chat = model.start_chat(history=typed_history)

        response = await chat.send_message_async(
            new_prompt,
            generation_config=generation_config if config_params_set else None,
            safety_settings=safety_settings
        )

        if not response.parts:
            block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Unknown block reason"
            logger.warning(f"Responce from Gemini blocked(context). Reason: {block_reason}")
            return None, f"{GEMINI_BLOCKED_ERROR}:{block_reason}"

        return response.text, None

    except api_core_exceptions.PermissionDenied as e:
        logger.error(f"Permission denied during text generation ({model_name}). Invalid API Key? Error: {e}", exc_info=False)
        return None, GEMINI_API_KEY_INVALID
    except api_core_exceptions.ResourceExhausted as e:
        logger.error(f"Quota exceeded during text generation ({model_name}): {e}", exc_info=False)
        return None, GEMINI_QUOTA_ERROR
    except api_core_exceptions.ServiceUnavailable as e:
        logger.warning(f"Service unavailable during text generation ({model_name}): {e}", exc_info=False)
        return None, GEMINI_SERVICE_UNAVAILABLE
    except api_core_exceptions.InvalidArgument as e:
        logger.error(f"Invalid argument during text generation ({model_name}): {e}", exc_info=True)
        return None, f"{GEMINI_REQUEST_ERROR}:InvalidArgument"
    except api_core_exceptions.GoogleAPIError as e:
        logger.error(f"Google API error during text generation ({model_name}): {e}", exc_info=True)
        return None, f"{GEMINI_UNKNOWN_API_ERROR}:{type(e).__name__}"
    except Exception as e:
        if "429" in str(e) and "quota" in str(e).lower():
            logger.error(f"Quota-like error caught in generic Exception ({model_name}): {e}", exc_info=False)
            return None, GEMINI_QUOTA_ERROR
        else:
            logger.error(f"Unexpected error during text generation ({model_name}): {e}", exc_info=True)
            return None, f"{GEMINI_REQUEST_ERROR}:{type(e).__name__}"


async def analyze_image(image_bytes: bytes, prompt: str) -> Tuple[str | None, str | None]:
    """
    Analyzes image using the Gemini API.
    Returns image description, error code or None.
    """
    if not (config and config.gemini.api_key):
        logger.error("Gemini API not configured for image analysis.")
        return None, GEMINI_API_KEY_ERROR

    try:
        img = PIL.Image.open(io.BytesIO(image_bytes))
        model = genai.GenerativeModel(VISION_MODEL)
        response = await model.generate_content_async([prompt, img], safety_settings=safety_settings)

        if not response.parts:
            block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Unknown block reason"
            logger.warning(f"Responce from Gemini ({VISION_MODEL}) blocked. Reason: {block_reason}")
            return None, f"{IMAGE_ANALYSIS_ERROR}:InvalidImageData"

        return response.text, None

    except api_core_exceptions.PermissionDenied as e:
        logger.error(f"Permission denied during image analysis ({VISION_MODEL}). Invalid API Key? Error: {e}", exc_info=False)
        return None, GEMINI_API_KEY_INVALID
    except api_core_exceptions.ResourceExhausted as e:
        logger.error(f"Quota exceeded during image analysis ({VISION_MODEL}): {e}", exc_info=False)
        return None, GEMINI_QUOTA_ERROR
    except api_core_exceptions.ServiceUnavailable as e:
        logger.warning(f"Service unavailable during image analysis ({VISION_MODEL}): {e}", exc_info=False)
        return None, GEMINI_SERVICE_UNAVAILABLE
    except (api_core_exceptions.InvalidArgument, ValueError) as e:
        logger.error(f"Invalid argument or image format during image analysis ({VISION_MODEL}): {e}", exc_info=True)
        return None, f"{IMAGE_ANALYSIS_ERROR}:InvalidData"
    except api_core_exceptions.GoogleAPIError as e:
        logger.error(f"Google API error during image analysis ({VISION_MODEL}): {e}", exc_info=True)
        return None, f"{GEMINI_UNKNOWN_API_ERROR}:{type(e).__name__}"
    except Exception as e:
        if "429" in str(e) and "quota" in str(e).lower():
            logger.error(f"Quota-like error caught in generic Exception ({VISION_MODEL}): {e}", exc_info=False)
            return None, GEMINI_QUOTA_ERROR
        else:
            logger.error(f"Unexpected error during image analysis ({VISION_MODEL}): {e}", exc_info=True)
            return None, f"{IMAGE_ANALYSIS_ERROR}:{type(e).__name__}"