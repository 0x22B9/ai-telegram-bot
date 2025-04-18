import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from typing import Union
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization

from src.db import get_user_settings, save_user_setting
from src.config import (
    ALLOWED_TEMPERATURES, ALLOWED_MAX_TOKENS,
    TEMPERATURE_NAMES, MAX_TOKENS_NAMES,
    DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
)
from src.keyboards import get_main_keyboard

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

@settings_router.message(Command("settings"))
async def handle_settings_command(message: types.Message, localizer: FluentLocalization):
    """Shows settings keyboard."""
    user_id = message.from_user.id
    keyboard = await build_settings_keyboard(user_id, localizer)
    settings_text = localizer.format_value("settings-current-prompt")
    main_reply_keyboard = get_main_keyboard(localizer)
    await message.answer(settings_text, reply_markup=keyboard.as_markup(), parse_mode=None)

@settings_router.callback_query(F.data == "settings:show")
async def cq_show_settings(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Shows settings keyboard (after pressing 'back')."""
    user_id = callback.from_user.id
    keyboard = await build_settings_keyboard(user_id, localizer)
    settings_text = localizer.format_value("settings-current-prompt")
    try:
        await callback.message.edit_text(settings_text, reply_markup=keyboard.as_markup(), parse_mode=None)
    except Exception as e:
        logger.error(f"Error while editing message for settings (user_id={user_id}): {e}")
    await callback.answer()

@settings_router.callback_query(F.data.startswith("settings:set:"))
async def cq_set_parameter(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Shows options for setting a parameter."""
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

    try:
        await callback.message.edit_text(prompt_text, reply_markup=builder.as_markup(), parse_mode=None)
    except Exception as e:
        logger.error(f"Error while editing message for settings {parameter} (user_id={user_id}): {e}")
    await callback.answer()


@settings_router.callback_query(F.data.startswith("settings:value:"))
async def cq_save_value(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Saves selected value and returns to settings."""
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
        setting_saved = await save_user_setting(user_id, db_field_name, final_value)

    if setting_saved:
        await cq_show_settings(callback, localizer)
    else:
        error_text = localizer.format_value("error-settings-save")
        await callback.answer(error_text, show_alert=True)