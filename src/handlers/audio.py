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
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization

from src.db import get_history, save_history
from src.handlers.text import (
    LAST_FAILED_PROMPT_KEY,
    RETRY_CALLBACK_DATA,
    _process_text_input,
    create_gemini_message,
    send_typing_periodically,
)
from src.keyboards import get_main_keyboard
from src.services import gemini
from src.services.errors import (
    DATABASE_SAVE_ERROR,
    TELEGRAM_DOWNLOAD_ERROR,
    TELEGRAM_MESSAGE_DELETED_ERROR,
    TELEGRAM_NETWORK_ERROR,
    format_error_message,
)
from src.services.gemini import (
    GEMINI_API_KEY_ERROR,
    GEMINI_BLOCKED_ERROR,
    GEMINI_QUOTA_ERROR,
    GEMINI_TRANSCRIPTION_ERROR,
)

logger = logging.getLogger(__name__)
audio_router = Router()


@audio_router.message(F.voice, StateFilter(None))
async def handle_voice_message(
    message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization
):
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Got audio message from user_id={user_id}")

    processing_voice_text = localizer.format_value("processing-voice")
    status_message = await message.answer(processing_voice_text)

    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))

    transcribed_text: Optional[str] = None
    transcription_error_code: Optional[str] = None
    final_response: str = localizer.format_value("error-general")
    updated_history = None
    failed_prompt_for_retry = None
    save_needed = False
    download_error = False

    try:
        voice = message.voice
        audio_bytes_io = io.BytesIO()
        try:
            logger.debug(f"Downloading voice {voice.file_id}...")
            await bot.download(file=voice, destination=audio_bytes_io)
            audio_bytes = audio_bytes_io.getvalue()
            logger.debug(
                f"Audio downloaded ({len(audio_bytes)} bytes), mime_type={voice.mime_type}"
            )

            if not audio_bytes:
                raise ValueError("Downloaded audio bytes are empty.")

        except (TelegramNetworkError, TelegramBadRequest, Exception) as e:
            logger.error(
                f"Failed to download voice {voice.file_id} for user {user_id}: {e}",
                exc_info=True,
            )
            final_response, _ = format_error_message(TELEGRAM_DOWNLOAD_ERROR, localizer)
            download_error = True

        if not download_error:
            transcribed_text, transcription_error_code = await gemini.transcribe_audio(
                audio_bytes=audio_bytes, mime_type=voice.mime_type
            )

            if transcribed_text and not transcription_error_code:
                logger.info(
                    f"Transcribed for user_id={user_id}: {transcribed_text[:100]}..."
                )
                processing_text_status = localizer.format_value(
                    "processing-transcribed-text"
                )
                try:
                    await status_message.edit_text(processing_text_status)
                except TelegramBadRequest as e_edit:
                    if "message to edit not found" not in str(e_edit).lower():
                        logger.warning(
                            f"Could not edit status message for transcription: {e_edit}"
                        )
                except Exception as e_edit_unexp:
                    logger.warning(
                        f"Unexpected error editing status message: {e_edit_unexp}"
                    )

                (
                    final_response,
                    updated_history,
                    failed_prompt_for_retry,
                ) = await _process_text_input(
                    user_text=transcribed_text,
                    user_id=user_id,
                    state=state,
                    localizer=localizer,
                )
                save_needed = (
                    updated_history is not None and failed_prompt_for_retry is None
                )

            elif transcription_error_code:
                logger.warning(
                    f"Transcription error for user_id={user_id}: {transcription_error_code}"
                )
                final_response, needs_retry = format_error_message(
                    transcription_error_code, localizer
                )
                if needs_retry:
                    pass
                if transcription_error_code.startswith(GEMINI_BLOCKED_ERROR):
                    user_msg_hist = create_gemini_message(
                        "user", "[Audio message - transcription blocked]"
                    )
                    current_history = await get_history(user_id)
                    updated_history = current_history + [user_msg_hist]
                    save_needed = True
                else:
                    save_needed = False
            else:
                logger.error(
                    f"Unexpected result from transcribe_audio for user_id={user_id}: no text, no error"
                )
                final_response, _ = format_error_message(None, localizer)
                save_needed = False

    except Exception as e:
        logger.exception(
            f"Critical error in voice handler logic for user_id={user_id}: {e}"
        )
        final_response, _ = format_error_message(None, localizer)
        save_needed = False
        failed_prompt_for_retry = None
    finally:
        audio_bytes_io.close()
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try:
                await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    reply_markup = None
    if failed_prompt_for_retry:
        await state.update_data({LAST_FAILED_PROMPT_KEY: failed_prompt_for_retry})
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value("button-retry-request")
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False

    message_sent_or_edited = False
    try:
        await status_message.edit_text(final_response, reply_markup=reply_markup)
        message_sent_or_edited = True
    except TelegramRetryAfter as e:
        logger.warning(
            f"Audio Handler: Flood control exceeded for user {user_id}: retry after {e.retry_after}s"
        )
        await asyncio.sleep(e.retry_after)
        try:
            await status_message.edit_text(final_response, reply_markup=reply_markup)
            message_sent_or_edited = True
        except Exception as retry_e:
            logger.error(
                f"Audio Handler: Failed to edit message even after RetryAfter for user {user_id}: {retry_e}"
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(
                f"Audio Handler: Message {status_message.message_id} is not modified."
            )
            message_sent_or_edited = True
        elif "message to edit not found" in str(e).lower():
            logger.warning(
                f"Audio Handler: Message {status_message.message_id} to edit not found for user {user_id}. Sending new message."
            )
            try:
                main_kbd = get_main_keyboard(localizer)
                await message.answer(
                    final_response, reply_markup=reply_markup or main_kbd
                )
                message_sent_or_edited = True
            except Exception as send_e:
                logger.error(
                    f"Audio Handler: Failed to send new message after edit failed for user {user_id}: {send_e}"
                )
        elif "can't parse entities" in str(e) or "nested entities" in str(e):
            logger.warning(
                f"Audio Handler: Parse error for user_id={user_id}. Sending plain text. Error: {e}"
            )
            try:
                await status_message.edit_text(
                    final_response, parse_mode=None, reply_markup=reply_markup
                )
                message_sent_or_edited = True
            except Exception as fallback_e:
                logger.error(
                    f"Audio Handler: Failed to send plain text for user_id={user_id}: {fallback_e}",
                    exc_info=True,
                )
                try:
                    await status_message.edit_text(
                        localizer.format_value("error-display")
                    )
                except Exception:
                    pass
        else:
            logger.error(
                f"Audio Handler: Unexpected TelegramBadRequest for user_id={user_id}: {e}",
                exc_info=True,
            )
            try:
                await status_message.edit_text(
                    localizer.format_value("error-telegram-send")
                )
            except Exception:
                pass
    except TelegramNetworkError as e:
        logger.error(
            f"Audio Handler: Network error while editing message for user {user_id}: {e}"
        )
        try:
            err_msg_net, _ = format_error_message(TELEGRAM_NETWORK_ERROR, localizer)
            await status_message.edit_text(err_msg_net)
        except Exception:
            pass
    except Exception as e:
        logger.exception(
            f"Audio Handler: Failed to edit final response for user_id={user_id}: {e}"
        )
        try:
            await status_message.edit_text(localizer.format_value("error-general"))
        except Exception:
            pass

    if save_needed and updated_history is not None and message_sent_or_edited:
        try:
            await save_history(user_id, updated_history)
        except Exception as db_save_e:
            logger.exception(
                f"Audio Handler: Failed to save history for user_id={user_id} to DB: {db_save_e}"
            )
            try:
                err_msg_db, _ = format_error_message(DATABASE_SAVE_ERROR, localizer)
                await message.answer(err_msg_db)
            except Exception as db_err_send_e:
                logger.error(
                    f"Audio Handler: Failed to send DB save error message to user {user_id}: {db_err_send_e}"
                )
    elif save_needed and updated_history is None:
        logger.error(
            f"Audio Handler: save_needed is True, but updated_history is None for user_id={user_id}!"
        )
