import asyncio
import logging

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatAction
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from fluent.runtime import FluentLocalization

from src.keyboards import get_main_keyboard
from src.services import image_generation as img_gen_service
from src.services.errors import (
    TELEGRAM_NETWORK_ERROR,
    TELEGRAM_UPLOAD_ERROR,
    format_error_message,
)

logger = logging.getLogger(__name__)
image_generation_router = Router()


class ImageGenState(StatesGroup):
    waiting_for_prompt = State()


async def send_upload_photo_periodically(bot: Bot, chat_id: int):
    """Sends 'upload_photo' action every 5 sec."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.debug(f"Upload_photo task for chat {chat_id} cancelled.")
    except Exception as e:
        logger.warning(
            f"Error in send_upload_photo_periodically for chat {chat_id}: {e}",
            exc_info=False,
        )


@image_generation_router.message(Command("generate_image"))
async def handle_generate_image_command(
    message: types.Message, state: FSMContext, localizer: FluentLocalization
):
    """Starts the image generation process."""
    prompt_request_text = localizer.format_value("generate-image-prompt")
    await message.answer(prompt_request_text)
    await state.set_state(ImageGenState.waiting_for_prompt)


@image_generation_router.message(ImageGenState.waiting_for_prompt, F.text)
async def handle_image_prompt(
    message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization
):
    """Gets prompt for image generation."""
    prompt = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Got image prompt from user_id={user_id}: {prompt[:50]}...")

    generating_text = localizer.format_value("generating-image")
    status_message = await message.answer(generating_text)

    typing_task = asyncio.create_task(send_upload_photo_periodically(bot, chat_id))

    image_bytes = None
    error_code = img_gen_service.IMAGE_GEN_UNKNOWN_ERROR
    final_response_text = ""

    try:
        image_bytes, error_code = await img_gen_service.generate_image_from_prompt(
            prompt
        )

        if image_bytes and error_code == img_gen_service.IMAGE_GEN_SUCCESS:
            photo_input = types.BufferedInputFile(
                image_bytes, filename="generated_image.png"
            )
            main_kbd = get_main_keyboard(localizer)
            caption_text = f"🖼️ {prompt[:900]}"

            try:
                await message.answer_photo(
                    photo=photo_input, caption=caption_text, reply_markup=main_kbd
                )
                logger.info(f"Generated image sent to user_id={user_id}")
                try:
                    await status_message.delete()
                except Exception as e_del:
                    logger.warning(
                        f"Could not delete status message {status_message.message_id}: {e_del}"
                    )

            except TelegramRetryAfter as e:
                logger.warning(
                    f"Image Gen: Flood control sending photo for user {user_id}: retry after {e.retry_after}s"
                )
                await asyncio.sleep(e.retry_after)
                try:
                    await message.answer_photo(
                        photo=photo_input, caption=caption_text, reply_markup=main_kbd
                    )
                    logger.info(
                        f"Generated image sent to user_id={user_id} after retry."
                    )
                    try:
                        await status_message.delete()
                    except Exception:
                        pass
                except Exception as retry_e:
                    logger.error(
                        f"Image Gen: Failed send photo after RetryAfter for user {user_id}: {retry_e}"
                    )
                    err_msg_upload, _ = format_error_message(
                        TELEGRAM_UPLOAD_ERROR, localizer
                    )
                    await status_message.edit_text(err_msg_upload)
            except (TelegramBadRequest, TelegramNetworkError) as e:
                logger.error(
                    f"Image Gen: Failed to send photo for user {user_id}: {e}",
                    exc_info=True,
                )
                error_key = (
                    TELEGRAM_NETWORK_ERROR
                    if isinstance(e, TelegramNetworkError)
                    else TELEGRAM_UPLOAD_ERROR
                )
                err_msg_upload, _ = format_error_message(error_key, localizer)
                try:
                    await status_message.edit_text(err_msg_upload)
                except Exception:
                    pass
            except Exception as e_send:
                logger.exception(
                    f"Image Gen: Unexpected error sending photo for user {user_id}: {e_send}"
                )
                err_msg_upload, _ = format_error_message(
                    TELEGRAM_UPLOAD_ERROR, localizer
                )
                try:
                    await status_message.edit_text(err_msg_upload)
                except Exception:
                    pass

        else:
            logger.warning(
                f"Image generation failed for user_id={user_id}: {error_code}"
            )
            final_response_text, _ = format_error_message(
                error_code, localizer, "error-image-unknown"
            )
            try:
                await status_message.edit_text(final_response_text)
            except Exception as e_edit_err:
                logger.error(
                    f"Image Gen: Could not edit status message with error: {e_edit_err}"
                )

    except Exception as e:
        logger.exception(
            f"Image Gen: Unexpected error in handler for user {user_id}: {e}"
        )
        final_response_text, _ = format_error_message(None, localizer)
        try:
            await status_message.edit_text(final_response_text)
        except Exception:
            pass
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try:
                await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        await state.clear()


@image_generation_router.message(ImageGenState.waiting_for_prompt)
async def handle_invalid_image_prompt_input(
    message: types.Message, localizer: FluentLocalization
):
    """Handles invalid image prompt input (e.g., photo instead of text)."""
    error_text = localizer.format_value("error-invalid-prompt-type")
    await message.reply(error_text)
