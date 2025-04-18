import logging
import io
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State
from fluent.runtime import FluentLocalization
import asyncio

from src.handlers.text import send_typing_periodically
from src.services import gemini
from src.utils.text_processing import strip_markdown

logger = logging.getLogger(__name__)

image_router = Router()

@image_router.message(F.photo, State(None))
async def handle_image_message(message: types.Message, bot: Bot, state: FSMContext, localizer: FluentLocalization):
    user_id = message.from_user.id
    logger.info(f"Got image from user_id={user_id} ({localizer.locales[0]}).")

    photo = message.photo[-1]

    thinking_message = await message.answer(localizer.format_value("analyzing"))

    image_bytes_io = io.BytesIO()
    try:
        await bot.download(file=photo, destination=image_bytes_io)
        image_bytes = image_bytes_io.getvalue()
        logger.debug(f"Image from user_id={user_id} downloaded ({len(image_bytes)} byte).")
    except Exception as e:
        logger.error(f"Error while downloading image for user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-image-download')
        await thinking_message.edit_text(error_msg)
        return
    finally:
        image_bytes_io.close()

    if message.caption:
        prompt = message.caption
        logger.info(f"Using caption from user_id={user_id}: {prompt}")
    else:
        prompt = localizer.format_value("prompt-describe-image-default")
        logger.info(f"Using default prompt for user_id={user_id}")

    typing_task = asyncio.create_task(send_typing_periodically(bot, message.chat.id))
    response_text = None
    error_code = None

    try:
        response_text, error_code = await gemini.analyze_image(image_bytes, prompt)
    finally:
         if typing_task and not typing_task.done():
             typing_task.cancel()
             try: await asyncio.wait_for(typing_task, timeout=0.1)
             except (asyncio.CancelledError, asyncio.TimeoutError): pass

    if response_text and not error_code:
        final_response = strip_markdown(response_text)
        await thinking_message.edit_text(final_response)
        logger.info(f"Image analysis Gemini for user_id={user_id} completed.")
    else:
        logger.warning(f"Error image analysis for user_id={user_id}: {error_code}")
        if error_code == gemini.IMAGE_ANALYSIS_ERROR:
            error_text = localizer.format_value("error-image-analysis-failed")
        elif error_code == gemini.GEMINI_API_KEY_ERROR:
            error_text = localizer.format_value('error-gemini-api-key')
        elif error_code and error_code.startswith(gemini.GEMINI_BLOCKED_ERROR):
            reason = error_code.split(":", 1)[1] if ":" in error_code else "Unknown"
            error_text = localizer.format_value('error-blocked-content', args={'reason': reason})
        else:
             error_text = localizer.format_value('error-image-analysis-unknown')
        await thinking_message.edit_text(error_text)