import asyncio
import io
import logging
from typing import Optional

from aiogram import Bot, F, Router, types
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from fluent.runtime import FluentLocalization

from src.handlers.text import send_typing_periodically
from src.keyboards import get_main_keyboard
from src.services import gemini
from src.services.errors import (
    TELEGRAM_DOWNLOAD_ERROR,
    TELEGRAM_NETWORK_ERROR,
    format_error_message,
)
from src.utils.text_processing import strip_markdown

logger = logging.getLogger(__name__)

image_router = Router()


@image_router.message(F.photo, State(None))
async def handle_image_message(
    message: types.Message, bot: Bot, state: FSMContext, localizer: FluentLocalization
):
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Got image from user_id={user_id} ({localizer.locales[0]}).")

    photo = message.photo[-1]

    thinking_message = await message.answer(localizer.format_value("analyzing"))
    image_bytes: Optional[bytes] = None
    image_bytes_io = io.BytesIO()
    download_error = False

    try:
        await bot.download(file=photo, destination=image_bytes_io)
        image_bytes = image_bytes_io.getvalue()
        if not image_bytes:
            raise ValueError("Downloaded image bytes are empty.")
        logger.debug(
            f"Image from user_id={user_id} downloaded ({len(image_bytes)} bytes)."
        )
    except (TelegramNetworkError, TelegramBadRequest, ValueError, Exception) as e:
        logger.error(
            f"Failed to download photo {photo.file_id} for user_id={user_id}: {e}",
            exc_info=True,
        )
        error_msg, _ = format_error_message(TELEGRAM_DOWNLOAD_ERROR, localizer)
        try:
            await thinking_message.edit_text(error_msg)
        except Exception:
            pass
        download_error = True
    finally:
        image_bytes_io.close()

    if download_error:
        return

    if message.caption:
        prompt = message.caption
        logger.info(f"Using caption from user_id={user_id}: {prompt}")
    else:
        prompt = localizer.format_value("prompt-describe-image-default")
        logger.info(f"Using default localized prompt for user_id={user_id}: '{prompt}'")

    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))
    response_text = None
    error_code = None
    final_response = localizer.format_value("error-general")

    try:
        response_text, error_code = await gemini.analyze_image(image_bytes, prompt)

        if response_text and not error_code:
            final_response = strip_markdown(response_text)
            logger.info(f"Image analysis for user_id={user_id} completed.")
        elif error_code:
            logger.warning(
                f"Error during image analysis for user_id={user_id}: {error_code}"
            )
            final_response, _ = format_error_message(
                error_code, localizer, "error-image-analysis-unknown"
            )
        else:
            logger.error(
                f"Unexpected result from image analysis for user_id={user_id}: no text and no error code."
            )
            final_response, _ = format_error_message(None, localizer)

    except Exception as e:
        logger.exception(
            f"Unexpected error during image analysis call for user {user_id}: {e}"
        )
        final_response, _ = format_error_message(None, localizer)
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try:
                await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    try:
        await thinking_message.edit_text(final_response)
    except TelegramRetryAfter as e:
        logger.warning(
            f"Image Handler: Flood control for user {user_id}: retry after {e.retry_after}s"
        )
        await asyncio.sleep(e.retry_after)
        try:
            await thinking_message.edit_text(final_response)
        except Exception as retry_e:
            logger.error(
                f"Image Handler: Failed edit after RetryAfter for user {user_id}: {retry_e}"
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(
                f"Image Handler: Message {thinking_message.message_id} not modified."
            )
        elif "message to edit not found" in str(e).lower():
            logger.warning(
                f"Image Handler: Message {thinking_message.message_id} not found for user {user_id}. Sending new."
            )
            try:
                main_kbd = get_main_keyboard(localizer)
                await message.answer(final_response, reply_markup=main_kbd)
            except Exception as send_e:
                logger.error(
                    f"Image Handler: Failed send new message for user {user_id}: {send_e}"
                )
        elif "can't parse entities" in str(e):
            logger.warning(
                f"Image Handler: Parse error for user_id={user_id}. Plain text. Error: {e}"
            )
            try:
                await thinking_message.edit_text(final_response, parse_mode=None)
            except Exception as fallback_e:
                logger.error(
                    f"Image Handler: Failed send plain text for user_id={user_id}: {fallback_e}",
                    exc_info=True,
                )
                try:
                    await thinking_message.edit_text(
                        localizer.format_value("error-display")
                    )
                except Exception:
                    pass
        else:
            logger.error(
                f"Image Handler: Unexpected TelegramBadRequest for user_id={user_id}: {e}",
                exc_info=True,
            )
            try:
                await thinking_message.edit_text(
                    localizer.format_value("error-telegram-send")
                )
            except Exception:
                pass
    except TelegramNetworkError as e:
        logger.error(
            f"Image Handler: Network error editing message for user {user_id}: {e}"
        )
        try:
            err_msg_net, _ = format_error_message(TELEGRAM_NETWORK_ERROR, localizer)
            await thinking_message.edit_text(err_msg_net)
        except Exception:
            pass
    except Exception as e:
        logger.exception(
            f"Image Handler: Failed edit final response for user_id={user_id}: {e}"
        )
        try:
            await thinking_message.edit_text(localizer.format_value("error-general"))
        except Exception:
            pass
