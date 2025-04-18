import logging
import asyncio
import io
from aiogram import Router, F, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from fluent.runtime import FluentLocalization
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional

from src.services import gemini
from src.handlers.text import _process_text_input, LAST_FAILED_PROMPT_KEY, RETRY_CALLBACK_DATA, send_typing_periodically
from src.services.gemini import GEMINI_TRANSCRIPTION_ERROR, GEMINI_QUOTA_ERROR, GEMINI_API_KEY_ERROR, GEMINI_BLOCKED_ERROR
from src.db import save_history

logger = logging.getLogger(__name__)
audio_router = Router()

@audio_router.message(F.voice, StateFilter(None))
async def handle_voice_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
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

    try:
        voice = message.voice
        audio_bytes_io = io.BytesIO()
        await bot.download(file=voice, destination=audio_bytes_io)
        audio_bytes = audio_bytes_io.getvalue()
        logger.debug(f"Audio downloaded ({len(audio_bytes)} byte), mime_type={voice.mime_type}")

        transcribed_text, transcription_error_code = await gemini.transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type=voice.mime_type
        )

        if transcribed_text and not transcription_error_code:
            logger.info(f"Transcribing for user_id={user_id}: {transcribed_text[:100]}...")
            processing_text_status = localizer.format_value("processing-transcribed-text")
            await status_message.edit_text(processing_text_status)

            final_response, updated_history, failed_prompt_for_retry = await _process_text_input(
                user_text=transcribed_text,
                user_id=user_id,
                state=state,
                localizer=localizer
            )
            save_needed = updated_history is not None and not failed_prompt_for_retry
        else:
            logger.warning(f"Error transcription for user_id={user_id}: {transcription_error_code}")
            if transcription_error_code == GEMINI_QUOTA_ERROR:
                final_response = localizer.format_value('error-quota-exceeded')
            elif transcription_error_code == GEMINI_API_KEY_ERROR:
                final_response = localizer.format_value('error-gemini-api-key')
            elif transcription_error_code and transcription_error_code.startswith(GEMINI_BLOCKED_ERROR):
                 reason = transcription_error_code.split(":", 1)[1] if ":" in transcription_error_code else "Unknown Error"
                 final_response = localizer.format_value('error-blocked-content', args={'reason': reason})
            elif transcription_error_code and transcription_error_code.startswith(GEMINI_TRANSCRIPTION_ERROR):
                 error_detail = transcription_error_code.split(":", 1)[1] if ":" in transcription_error_code else "Unknown Error"
                 final_response = localizer.format_value('error-transcription-failed', args={'error': error_detail})
            else:
                 final_response = localizer.format_value('error-transcription-failed-unknown')

    except Exception as e:
        logger.error(f"Error while processing voice message for user_id={user_id}: {e}", exc_info=True)
        final_response = localizer.format_value("error-processing-voice")
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    reply_markup = None
    if failed_prompt_for_retry:
        await state.update_data({LAST_FAILED_PROMPT_KEY: failed_prompt_for_retry})
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False

    try:
        await status_message.edit_text(final_response, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
             logger.debug(f"Message {status_message.message_id} (audio) was not modified.")
        elif "can't parse entities" in str(e) or "nested entities" in str(e):
            logger.warning(f"Parsing error after transcription for user_id={user_id}. Sending plain text. Error: {e}")
            try:
                await status_message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
            except Exception as fallback_e:
                logger.error(f"Can't send text after transcription plain text for user_id={user_id}: {fallback_e}", exc_info=True)
                error_msg = localizer.format_value('error-display')
                await status_message.edit_text(error_msg)
                save_needed = False
        else:
            logger.error(f"Unexpected error TelegramBadRequest after transcription for user_id={user_id}: {e}", exc_info=True)
            error_msg = localizer.format_value('error-telegram-send')
            await status_message.edit_text(error_msg)
            save_needed = False
    except Exception as e:
        logger.error(f"General error while editing message after transcription for user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-general')
        await status_message.edit_text(error_msg)
        save_needed = False
    if save_needed and updated_history:
        await save_history(user_id, updated_history)