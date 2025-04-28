import logging
import asyncio # Для sleep
from aiogram import Router, F, types
from aiogram.filters import Command
from typing import Union
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError, TelegramRetryAfter

from src.db import get_user_settings, save_user_setting
from src.config import (
    ALLOWED_TEMPERATURES, ALLOWED_MAX_TOKENS,
    TEMPERATURE_NAMES, MAX_TOKENS_NAMES,
    DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
)
from src.keyboards import get_main_keyboard
from src.services.errors import format_error_message, DATABASE_SAVE_ERROR, TELEGRAM_MESSAGE_DELETED_ERROR, TELEGRAM_NETWORK_ERROR

logger = logging.getLogger(__name__)
settings_router = Router()

async def build_settings_keyboard(user_id: int, localizer: FluentLocalization) -> InlineKeyboardBuilder:
    """Build inline keyboard for settings."""
    current_temp, current_max_tokens = await get_user_settings(user_id)

    temp_name = TEMPERATURE_NAMES.get(current_temp, f"{current_temp:.1f}")
    tokens_name = MAX_TOKENS_NAMES.get(current_max_tokens, str(current_max_tokens))

    builder = InlineKeyboardBuilder()
    temp_button_text = localizer.format_value("settings-button-temperature", args={"value": temp_name})
    builder.button(text=temp_button_text, callback_data="settings:set:temperature")
    tokens_button_text = localizer.format_value("settings-button-max-tokens", args={"value": tokens_name})
    builder.button(text=tokens_button_text, callback_data="settings:set:max_tokens")
    builder.adjust(1)
    return builder


async def _edit_settings_message(message: types.Message, text: str, markup: types.InlineKeyboardMarkup, localizer: FluentLocalization):
    """Вспомогательная функция для редактирования сообщения с обработкой ошибок."""
    try:
        await message.edit_text(text, reply_markup=markup, parse_mode=None)
    except TelegramRetryAfter as e:
        logger.warning(f"Settings: Flood control editing settings for user {message.chat.id}: retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        try: await message.edit_text(text, reply_markup=markup, parse_mode=None)
        except Exception: pass
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
             logger.debug(f"Settings: Message {message.message_id} not modified.")
        elif "message to edit not found" in str(e).lower():
             logger.warning(f"Settings: Message {message.message_id} not found.")
        else:
             logger.error(f"Settings: Error editing message {message.message_id}: {e}")
    except TelegramNetworkError as e_net:
         logger.error(f"Settings: Network error editing message {message.message_id}: {e_net}")
    except Exception as e_unexp:
         logger.error(f"Settings: Unexpected error editing message {message.message_id}: {e_unexp}", exc_info=True)


@settings_router.message(Command("settings"))
async def handle_settings_command(message: types.Message, localizer: FluentLocalization):
    """Shows settings keyboard."""
    user_id = message.from_user.id
    try:
        keyboard = await build_settings_keyboard(user_id, localizer)
        settings_text = localizer.format_value("settings-current-prompt")
        await message.answer(settings_text, reply_markup=keyboard.as_markup(), parse_mode=None)
    except Exception as e:
         logger.error(f"Settings: Error sending settings message for user {user_id}: {e}", exc_info=True)
         await message.answer(localizer.format_value('error-general'))


@settings_router.callback_query(F.data == "settings:show")
async def cq_show_settings(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Shows settings keyboard (after pressing 'back')."""
    user_id = callback.from_user.id
    if not callback.message: return

    keyboard = await build_settings_keyboard(user_id, localizer)
    settings_text = localizer.format_value("settings-current-prompt")
    await _edit_settings_message(callback.message, settings_text, keyboard.as_markup(), localizer)
    try: await callback.answer()
    except Exception: pass


@settings_router.callback_query(F.data.startswith("settings:set:"))
async def cq_set_parameter(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Shows options for setting a parameter."""
    if not callback.message: return
    try:
        parameter = callback.data.split(":")[2]
    except IndexError:
        logger.warning(f"Incorrect callback_data 'settings:set:': {callback.data}")
        await callback.answer("Error!", show_alert=True)
        return

    user_id = callback.from_user.id
    current_temp, current_max_tokens = await get_user_settings(user_id)

    builder = InlineKeyboardBuilder()
    prompt_text = ""

    if parameter == "temperature":
        prompt_text = localizer.format_value("settings-prompt-temperature")
        default_temp_text = localizer.format_value("settings-option-default", args={"value": f"{DEFAULT_GEMINI_TEMPERATURE:.1f}"})
        is_current = (current_temp == DEFAULT_GEMINI_TEMPERATURE)
        builder.button(
            text=f"✅ {default_temp_text}" if is_current else default_temp_text,
            callback_data=f"settings:value:temperature:{DEFAULT_GEMINI_TEMPERATURE}"
        )
        for name, value in ALLOWED_TEMPERATURES.items():
            is_current = (abs(current_temp - value) < 0.01)
            button_text = localizer.format_value(f"settings-option-temperature-{name}")
            builder.button(
                text=f"✅ {button_text}" if is_current else button_text,
                callback_data=f"settings:value:temperature:{value}"
            )

    elif parameter == "max_tokens":
        prompt_text = localizer.format_value("settings-prompt-max-tokens")
        default_tokens_text = localizer.format_value("settings-option-default", args={"value": str(DEFAULT_GEMINI_MAX_TOKENS)})
        is_current = (current_max_tokens == DEFAULT_GEMINI_MAX_TOKENS)
        builder.button(
            text=f"✅ {default_tokens_text}" if is_current else default_tokens_text,
            callback_data=f"settings:value:max_tokens:{DEFAULT_GEMINI_MAX_TOKENS}"
        )
        for name, value in ALLOWED_MAX_TOKENS.items():
            is_current = (current_max_tokens == value)
            button_text = localizer.format_value(f"settings-option-max-tokens-{name}")
            builder.button(
                text=f"✅ {button_text}" if is_current else button_text,
                callback_data=f"settings:value:max_tokens:{value}"
            )
    else:
        logger.warning(f"Unknown parameter in 'settings:set:': {parameter}")
        await callback.answer("Unknown parameter!", show_alert=True)
        return

    back_button_text = localizer.format_value("button-back")
    builder.button(text=back_button_text, callback_data="settings:show")
    builder.adjust(1)

    await _edit_settings_message(callback.message, prompt_text, builder.as_markup(), localizer)
    try: await callback.answer()
    except Exception: pass


@settings_router.callback_query(F.data.startswith("settings:value:"))
async def cq_save_value(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Saves selected value and returns to settings."""
    if not callback.message: return
    try:
        parts = callback.data.split(":")
        parameter = parts[2]
        value_str = parts[3]
    except IndexError:
        logger.warning(f"Incorrect callback_data 'settings:value:': {callback.data}")
        await callback.answer("Error!", show_alert=True)
        return

    user_id = callback.from_user.id
    setting_saved = False
    db_field_name = ""
    final_value: Union[float, int, None] = None
    error_text = ""

    if parameter == "temperature":
        db_field_name = "gemini_temperature"
        try:
            final_value = float(value_str)
            allowed_values_list = list(ALLOWED_TEMPERATURES.values()) + [DEFAULT_GEMINI_TEMPERATURE]
            if not any(abs(final_value - v) < 0.01 for v in allowed_values_list):
                 raise ValueError("Value not in allowed list")
        except ValueError:
            logger.warning(f"Incorrect value for temperature '{value_str}' from user_id={user_id}")
            await callback.answer("Incorrect value!", show_alert=True)
            return

    elif parameter == "max_tokens":
        db_field_name = "gemini_max_tokens"
        try:
            final_value = int(value_str)
            allowed_values_list = list(ALLOWED_MAX_TOKENS.values()) + [DEFAULT_GEMINI_MAX_TOKENS]
            if final_value not in allowed_values_list:
                raise ValueError("Value not in allowed list")
        except ValueError:
            logger.warning(f"Incorrect value for max_tokens '{value_str}' from user_id={user_id}")
            await callback.answer("Incorrect value!", show_alert=True)
            return
    else:
        logger.warning(f"Unknown parameter in 'settings:value:': {parameter}")
        await callback.answer("Unknown parameter!", show_alert=True)
        return

    if final_value is not None:
        try:
            setting_saved = await save_user_setting(user_id, db_field_name, final_value)
            if not setting_saved:
                 logger.error(f"Settings: save_user_setting returned False for user {user_id}, field {db_field_name}")
                 error_text, _ = format_error_message(DATABASE_SAVE_ERROR, localizer)
        except Exception as e_db:
             logger.exception(f"Settings: Error saving setting for user {user_id} to DB: {e_db}")
             error_text, _ = format_error_message(DATABASE_SAVE_ERROR, localizer)

    if setting_saved:
        await cq_show_settings(callback, localizer)
    else:
        final_error_text = error_text or localizer.format_value("error-settings-save")
        try:
            await callback.answer(final_error_text, show_alert=True)
        except Exception as e_ans:
             logger.warning(f"Settings: Could not answer callback with error for user {user_id}: {e_ans}")