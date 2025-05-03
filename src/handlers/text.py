import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatAction
from aiogram.exceptions import (  # Добавили исключения
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization

from src.config import DEFAULT_TEXT_MODEL
from src.db import get_history, get_user_settings, save_history
from src.keyboards import get_main_keyboard
from src.services import gemini
from src.services.errors import (
    DATABASE_SAVE_ERROR,
    TELEGRAM_MESSAGE_DELETED_ERROR,
    TELEGRAM_NETWORK_ERROR,
    format_error_message,
)
from src.services.gemini import (
    GEMINI_API_KEY_ERROR,
    GEMINI_API_KEY_INVALID,
    GEMINI_BLOCKED_ERROR,
    GEMINI_QUOTA_ERROR,
    GEMINI_REQUEST_ERROR,
    GEMINI_SERVICE_UNAVAILABLE,
    GEMINI_UNKNOWN_API_ERROR,
)
from src.utils.text_processing import strip_markdown

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
        logger.warning(
            f"Error in send_typing_periodically for chat {chat_id}: {e}", exc_info=False
        )


async def _process_text_input(
    user_text: str, user_id: int, state: FSMContext, localizer: FluentLocalization
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
        logger.debug(
            f"Processing text with: model={selected_model}, temp={user_temp}, tokens={user_max_tokens}"
        )

        response_text, error_code = await gemini.generate_text_with_history(
            history=current_history,
            new_prompt=user_text,
            model_name=selected_model,
            temperature=user_temp,
            max_output_tokens=user_max_tokens,
        )

        if response_text and not error_code:
            final_response = strip_markdown(response_text)
            user_msg_hist = create_gemini_message("user", user_text)
            model_msg_hist = create_gemini_message("model", response_text)
            updated_history = current_history + [user_msg_hist, model_msg_hist]
            logger.info(f"Gemini ({selected_model}) responsed for user_id={user_id}.")
        elif error_code:
            logger.warning(
                f"Error from Gemini ({selected_model}) for user_id={user_id}: {error_code}"
            )
            final_response, needs_retry = format_error_message(error_code, localizer)
            if needs_retry:
                failed_prompt_for_retry = user_text
            if error_code.startswith(gemini.GEMINI_BLOCKED_ERROR):
                user_msg_hist = create_gemini_message("user", user_text)
                updated_history = current_history + [user_msg_hist]
            else:
                updated_history = None
        else:
            logger.error(
                f"Unexpected result from Gemini ({selected_model}) for user_id={user_id}: no text and no error code."
            )
            final_response, _ = format_error_message(None, localizer)
            failed_prompt_for_retry = user_text

        return final_response, updated_history, failed_prompt_for_retry

    except Exception as e:
        logger.error(
            f"Unexpected error in _process_text_input for user_id={user_id}: {e}",
            exc_info=True,
        )
        final_response, _ = format_error_message(None, localizer)
        return final_response, None, None


@text_router.message(F.text & ~F.text.startswith("/"), StateFilter(None))
async def handle_text_message(
    message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization
):
    user_text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(
        f"Text from user_id={user_id} ({localizer.locales[0]}): {user_text[:50]}..."
    )

    await state.update_data({LAST_FAILED_PROMPT_KEY: None})
    thinking_text = localizer.format_value("thinking")
    thinking_message = await message.answer(thinking_text)
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))

    final_response = localizer.format_value("error-general")
    updated_history = None
    failed_prompt = None
    save_needed = False

    try:
        final_response, updated_history, failed_prompt = await _process_text_input(
            user_text=user_text, user_id=user_id, state=state, localizer=localizer
        )
        save_needed = updated_history is not None and failed_prompt is None
    except Exception as e:
        logger.exception(
            f"Critical error in handler logic for user_id={user_id} while processing text: {e}"
        )
        final_response, _ = format_error_message(None, localizer)
        save_needed = False
        failed_prompt = None
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try:
                await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    reply_markup = None
    if failed_prompt:
        await state.update_data({LAST_FAILED_PROMPT_KEY: failed_prompt})
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value("button-retry-request")
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False

    try:
        await thinking_message.edit_text(final_response, reply_markup=reply_markup)
    except TelegramRetryAfter as e:
        logger.warning(
            f"Flood control exceeded for user {user_id}: retry after {e.retry_after}s"
        )
        await asyncio.sleep(e.retry_after)
        try:
            await thinking_message.edit_text(final_response, reply_markup=reply_markup)
        except Exception as retry_e:
            logger.error(
                f"Failed to edit message even after RetryAfter for user {user_id}: {retry_e}"
            )
            save_needed = False
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(f"Message {thinking_message.message_id} is not modified.")
        elif "message to edit not found" in str(e).lower():
            logger.warning(
                f"Message {thinking_message.message_id} to edit not found for user {user_id}. Sending new message."
            )
            try:
                main_kbd = get_main_keyboard(localizer)
                await message.answer(
                    final_response, reply_markup=reply_markup or main_kbd
                )
            except Exception as send_e:
                logger.error(
                    f"Failed to send new message after edit failed for user {user_id}: {send_e}"
                )
                save_needed = False
        elif "can't parse entities" in str(e):
            logger.warning(
                f"HTML Parse error for user_id={user_id}. Sending plain text."
            )
            try:
                await thinking_message.edit_text(
                    final_response, parse_mode=None, reply_markup=reply_markup
                )
            except Exception as fallback_e:
                logger.error(
                    f"Failed to send plain text for user_id={user_id}: {fallback_e}",
                    exc_info=True,
                )
                await thinking_message.edit_text(
                    localizer.format_value("error-display")
                )
        else:
            logger.error(
                f"Unexpected TelegramBadRequest for user_id={user_id}: {e}",
                exc_info=True,
            )
            await thinking_message.edit_text(
                localizer.format_value("error-telegram-send")
            )
            save_needed = False
    except TelegramNetworkError as e:
        logger.error(f"Network error while editing message for user {user_id}: {e}")
        await thinking_message.edit_text(
            localizer.format_value("error-telegram-network")
        )
        save_needed = False
    except Exception as e:
        logger.exception(f"Failed to edit final response for user_id={user_id}: {e}")
        try:
            await thinking_message.edit_text(localizer.format_value("error-general"))
        except Exception:
            pass
        save_needed = False

    if save_needed and updated_history is not None:
        try:
            await save_history(user_id, updated_history)
        except Exception as db_save_e:
            logger.exception(
                f"Failed to save history for user_id={user_id} to DB: {db_save_e}"
            )
            await message.answer(localizer.format_value("error-db-save"))
    elif save_needed and updated_history is None:
        logger.error(
            f"Flag save_needed is True, but updated_history is None for user_id={user_id}!"
        )


@text_router.callback_query(F.data == RETRY_CALLBACK_DATA)
async def handle_retry_request(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: Bot,
    localizer: FluentLocalization,
):
    await callback.answer()
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id if callback.message else user_id
    user_data = await state.get_data()
    original_prompt = user_data.get(LAST_FAILED_PROMPT_KEY)

    try:
        await callback.answer()
    except Exception as e_ans:
        logger.warning(
            f"Retry Handler: Could not answer callback for user {user_id}: {e_ans}"
        )

    if not original_prompt:
        logger.warning(
            f"Retry Handler: Text for retry not found for user_id={user_id}."
        )
        if callback.message:
            try:
                await callback.message.edit_text(
                    localizer.format_value("error-retry-not-found"), reply_markup=None
                )
            except Exception as e_edit:
                logger.error(
                    f"Retry Handler: Error editing 'retry not found' message for user_id={user_id}: {e_edit}"
                )
        return

    logger.info(f"Retrying request for user_id={user_id}: {original_prompt[:50]}...")
    retry_status_text = localizer.format_value("thinking-retry")
    status_message = callback.message

    if status_message:
        try:
            await status_message.edit_text(retry_status_text, reply_markup=None)
        except Exception as e_edit_status:
            logger.warning(
                f"Retry Handler: Could not update status before retrying for user_id={user_id}: {e_edit_status}"
            )
    else:
        logger.warning(
            f"Retry Handler: No message found in callback for user {user_id}. Cannot edit status."
        )

    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))
    final_response = localizer.format_value("error-general")  # Default
    updated_history = None
    failed_prompt = None
    save_needed = False

    try:
        final_response, updated_history, failed_prompt = await _process_text_input(
            user_text=original_prompt, user_id=user_id, state=state, localizer=localizer
        )
        if not failed_prompt and updated_history is not None:
            await state.update_data({LAST_FAILED_PROMPT_KEY: None})
            save_needed = True
        else:
            save_needed = False

    except Exception as e:
        logger.exception(
            f"Retry Handler: Critical error in handler logic for user_id={user_id}: {e}"
        )
        final_response, _ = format_error_message(None, localizer)
        save_needed = False
        failed_prompt = None
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try:
                await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    reply_markup = None
    if failed_prompt:
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value("button-retry-request")
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False

    message_sent_or_edited = False
    if status_message:
        try:
            await status_message.edit_text(final_response, reply_markup=reply_markup)
            message_sent_or_edited = True
        except TelegramRetryAfter as e:
            logger.warning(
                f"Retry Handler: Flood control for user {user_id}: retry after {e.retry_after}s"
            )
            await asyncio.sleep(e.retry_after)
            try:
                await status_message.edit_text(
                    final_response, reply_markup=reply_markup
                )
                message_sent_or_edited = True
            except Exception as retry_e:
                logger.error(
                    f"Retry Handler: Failed edit after RetryAfter for user {user_id}: {retry_e}"
                )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logger.debug(
                    f"Retry Handler: Message {status_message.message_id} not modified."
                )
                message_sent_or_edited = True
            elif "message to edit not found" in str(e).lower():
                logger.warning(
                    f"Retry Handler: Message {status_message.message_id} not found for user {user_id}. Sending new."
                )
                try:
                    main_kbd = get_main_keyboard(localizer)
                    await bot.send_message(
                        chat_id, final_response, reply_markup=reply_markup or main_kbd
                    )
                    message_sent_or_edited = True
                except Exception as send_e:
                    logger.error(
                        f"Retry Handler: Failed send new message for user {user_id}: {send_e}"
                    )
            elif "can't parse entities" in str(e):
                logger.warning(
                    f"Retry Handler: Parse error for user_id={user_id}. Plain text. Error: {e}"
                )
                try:
                    await status_message.edit_text(
                        final_response, parse_mode=None, reply_markup=reply_markup
                    )
                    message_sent_or_edited = True
                except Exception as fallback_e:
                    logger.error(
                        f"Retry Handler: Failed send plain text for user_id={user_id}: {fallback_e}",
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
                    f"Retry Handler: Unexpected TelegramBadRequest for user_id={user_id}: {e}",
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
                f"Retry Handler: Network error editing message for user {user_id}: {e}"
            )
            try:
                err_msg_net, _ = format_error_message(TELEGRAM_NETWORK_ERROR, localizer)
                await status_message.edit_text(err_msg_net)
            except Exception:
                pass
        except Exception as e:
            logger.exception(
                f"Retry Handler: Failed edit final response for user_id={user_id}: {e}"
            )
            try:
                await status_message.edit_text(localizer.format_value("error-general"))
            except Exception:
                pass
    else:
        logger.warning(
            f"Retry Handler: status_message was None for user {user_id}, sending new."
        )
        try:
            main_kbd = get_main_keyboard(localizer)
            await bot.send_message(
                chat_id, final_response, reply_markup=reply_markup or main_kbd
            )
            message_sent_or_edited = True
        except Exception as e_send:
            logger.error(
                f"Retry Handler: Failed to send fallback message for user {user_id}: {e_send}"
            )

    if save_needed and updated_history is not None and message_sent_or_edited:
        try:
            await save_history(user_id, updated_history)
        except Exception as db_save_e:
            logger.exception(
                f"Retry Handler: Failed to save history for user_id={user_id} to DB: {db_save_e}"
            )
            try:
                err_msg_db, _ = format_error_message(DATABASE_SAVE_ERROR, localizer)
                await bot.send_message(chat_id, err_msg_db)
            except Exception as db_err_send_e:
                logger.error(
                    f"Retry Handler: Failed send DB save error message to user {user_id}: {db_err_send_e}"
                )
    elif save_needed and updated_history is None:
        logger.error(
            f"Retry Handler: save_needed is True, but updated_history is None for user_id={user_id}!"
        )
