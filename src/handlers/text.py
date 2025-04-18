import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization
from typing import List, Dict, Any, Tuple, Optional
import asyncio

from src.utils.text_processing import strip_markdown
from src.services import gemini
from src.db import get_history, get_user_settings, save_history 
from src.services.gemini import (
    GEMINI_API_KEY_ERROR, GEMINI_BLOCKED_ERROR, GEMINI_REQUEST_ERROR, GEMINI_QUOTA_ERROR
)
from src.config import DEFAULT_TEXT_MODEL
from src.keyboards import get_main_keyboard

logger = logging.getLogger(__name__)
text_router = Router()

LAST_FAILED_PROMPT_KEY = "last_failed_prompt"
RETRY_CALLBACK_DATA = "retry_last_prompt"

def create_gemini_message(role: str, text: str) -> Dict[str, Any]:
    """Creates message in format that Gemini API expects."""
    return {"role": role, "parts": [{"text": text}]}

async def send_typing_periodically(bot: Bot, chat_id: int):
    """Sends 'typing' every 4 sec, while task is not cancelled."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        logger.debug(f"Typing task for chat {chat_id} cancelled.")
        pass
    except Exception as e:
        logger.error(f"Error in send_typing_periodically for chat {chat_id}: {e}", exc_info=True)

async def _process_text_input(
    user_text: str,
    user_id: int,
    state: FSMContext,
    localizer: FluentLocalization
) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Processes user text input: queries Gemini, processes the response.
    Returns: (response_text_to_user, updated_history_for_saving | None, original_query_text_for_retry | None)
    """
    updated_history = None
    failed_prompt_for_retry = None

    try:
        current_history = await get_history(user_id)
        user_temp, user_max_tokens = await get_user_settings(user_id)
        user_data = await state.get_data()
        selected_model = user_data.get("selected_model", DEFAULT_TEXT_MODEL)
        logger.debug(f"Processing text with: model={selected_model}, temp={user_temp}, tokens={user_max_tokens}")

        response_text, error_code = await gemini.generate_text_with_history(
            history=current_history,
            new_prompt=user_text,
            model_name=selected_model,
            temperature=user_temp,
            max_output_tokens=user_max_tokens
        )

        if response_text and not error_code:
            final_response = strip_markdown(response_text)
            user_msg_hist = create_gemini_message("user", user_text)
            model_msg_hist = create_gemini_message("model", response_text)
            updated_history = current_history + [user_msg_hist, model_msg_hist]
            logger.info(f"Gemini ({selected_model}) responsed for user_id={user_id}.")
        elif error_code:
            logger.warning(f"Error from Gemini ({selected_model}) for user_id={user_id}: {error_code}")
            if error_code == GEMINI_QUOTA_ERROR:
                final_response = localizer.format_value('error-quota-exceeded')
            elif error_code.startswith(GEMINI_REQUEST_ERROR):
                error_detail = error_code.split(":", 1)[1] if ":" in error_code else "Unknown Error"
                final_response = localizer.format_value('error-gemini-request', args={'error': error_detail})
                failed_prompt_for_retry = user_text
            elif error_code == GEMINI_API_KEY_ERROR:
                final_response = localizer.format_value('error-gemini-api-key')
            elif error_code.startswith(GEMINI_BLOCKED_ERROR):
                reason = error_code.split(":", 1)[1] if ":" in error_code else "Unknown Reason"
                final_response = localizer.format_value('error-blocked-content', args={'reason': reason})
                user_msg_hist = create_gemini_message("user", user_text)
                updated_history = current_history + [user_msg_hist]
            else:
                final_response = localizer.format_value('error-general')
        else:
            logger.error(f"Unexpected result from Gemini ({selected_model}) for user_id={user_id}: there's no text and no error code.")
            final_response = localizer.format_value('error-gemini-fetch')
            failed_prompt_for_retry = user_text

        return final_response, updated_history, failed_prompt_for_retry

    except Exception as e:
        logger.error(f"Unexpected error in _process_text_input for user_id={user_id}: {e}", exc_info=True)
        final_response = localizer.format_value("error-general")
        return final_response, None, None

@text_router.message(
    F.text & ~F.text.startswith('/'),
    StateFilter(None)
)
async def handle_text_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    user_text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Text from user_id={user_id} ({localizer.locales[0]}): {user_text[:50]}...")

    await state.update_data({LAST_FAILED_PROMPT_KEY: None})
    thinking_text = localizer.format_value('thinking')
    thinking_message = await message.answer(thinking_text)
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))

    final_response = localizer.format_value("error-general")
    updated_history = None
    failed_prompt = None

    try:
        final_response, updated_history, failed_prompt = await _process_text_input(
            user_text=user_text,
            user_id=user_id,
            state=state,
            localizer=localizer
        )
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    reply_markup = None
    save_needed = updated_history is not None

    if failed_prompt:
        await state.update_data({LAST_FAILED_PROMPT_KEY: failed_prompt})
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False

    try:
        await thinking_message.edit_text(final_response, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
             logger.debug(f"Message {thinking_message.message_id} is not modified.")
        elif "can't parse entities" in str(e):
            logger.warning(f"HTML Parse error for user_id={user_id}. Sending plain text.")
            try:
                await thinking_message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
            except Exception as fallback_e:
                logger.error(f"Can't send plain text for user_id={user_id}: {fallback_e}", exc_info=True)
                error_msg = localizer.format_value('error-display')
                await thinking_message.edit_text(error_msg)
                save_needed = False
        else:
            logger.error(f"Unexpected error TelegramBadRequest for user_id={user_id}: {e}", exc_info=True)
            error_msg = localizer.format_value('error-general')
            await thinking_message.edit_text(error_msg)
            save_needed = False
    except Exception as e:
        logger.error(f"General error while editing message for user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-general')
        await thinking_message.edit_text(error_msg)
        save_needed = False

    if save_needed and updated_history is not None:
        await save_history(user_id, updated_history)
    elif save_needed and updated_history is None:
         logger.error(f"Trying to save history for user_id={user_id}, but updated_history is None!")


@text_router.callback_query(F.data == RETRY_CALLBACK_DATA)
async def handle_retry_request(callback: types.CallbackQuery, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    await callback.answer()
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id if callback.message else user_id
    user_data = await state.get_data()
    original_prompt = user_data.get(LAST_FAILED_PROMPT_KEY)

    if not original_prompt:
        logger.warning(f"Text for retry not found (user_id={user_id}). Maybe the message was deleted?")
        try:
            if callback.message:
                await callback.message.edit_text(localizer.format_value('error-retry-not-found'), reply_markup=None)
        except Exception as e:
            logger.error(f"Error while editing message for 'retry not found' for user_id={user_id}: {e}")
        return

    logger.info(f"Retrying request for user_id={user_id}: {original_prompt[:50]}...")
    retry_status_text = localizer.format_value('thinking-retry')
    status_message = None
    if callback.message:
        try:
            await callback.message.edit_text(retry_status_text, reply_markup=None)
            status_message = callback.message
        except Exception as e: logger.warning(f"Can't update status before retrying for user_id={user_id}: {e}")
    else:
        status_message = await bot.send_message(chat_id, retry_status_text)

    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))
    final_response = localizer.format_value("error-general")
    updated_history = None
    failed_prompt = None

    try:
        final_response, updated_history, failed_prompt = await _process_text_input(
            user_text=original_prompt,
            user_id=user_id,
            state=state,
            localizer=localizer
        )
        if not failed_prompt and updated_history is not None:
             await state.update_data({LAST_FAILED_PROMPT_KEY: None})

    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    reply_markup = None
    save_needed = updated_history is not None

    if failed_prompt:
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False

    if status_message:
        try:
            await status_message.edit_text(final_response, reply_markup=reply_markup)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e): pass
            elif "can't parse entities" in str(e):
                logger.warning(f"HTML Parse error while retrying for user_id={user_id}.")
                try: await status_message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
                except Exception as fallback_e: logger.error(f"Can't send plain text while retrying for user_id={user_id}: {fallback_e}", exc_info=True); save_needed = False
            else:
                logger.error(f"Unexpected error TelegramBadRequest while retrying for user_id={user_id}: {e}", exc_info=True); save_needed = False
        except Exception as e:
            logger.error(f"General error while editing message while retrying for user_id={user_id}: {e}", exc_info=True); save_needed = False
    else:
        main_kbd = get_main_keyboard(localizer)
        await bot.send_message(chat_id, final_response, reply_markup=main_kbd)

    if save_needed and updated_history is not None:
        await save_history(user_id, updated_history)
    elif save_needed and updated_history is None:
        logger.error(f"Trying to save history when retrying for user_id={user_id}, but updated_history is None!")