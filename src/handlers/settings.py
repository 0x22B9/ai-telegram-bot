import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from typing import Union
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization

from src.db import get_user_settings, save_user_setting
# Импортируем разрешенные значения и имена из config
from src.config import (
    ALLOWED_TEMPERATURES, ALLOWED_MAX_TOKENS,
    TEMPERATURE_NAMES, MAX_TOKENS_NAMES,
    DEFAULT_GEMINI_TEMPERATURE, DEFAULT_GEMINI_MAX_TOKENS
)
# Импортируем функцию для основной клавиатуры
from src.keyboards import get_main_keyboard

logger = logging.getLogger(__name__)
settings_router = Router()

# --- Вспомогательная функция для построения клавиатуры настроек ---
async def build_settings_keyboard(user_id: int, localizer: FluentLocalization) -> InlineKeyboardBuilder:
    """Строит inline клавиатуру для главного экрана настроек."""
    current_temp, current_max_tokens = await get_user_settings(user_id)

    # Получаем 'имя' для текущего значения или показываем само значение
    temp_name = TEMPERATURE_NAMES.get(current_temp, f"{current_temp:.1f}")
    tokens_name = MAX_TOKENS_NAMES.get(current_max_tokens, str(current_max_tokens))

    builder = InlineKeyboardBuilder()
    # Кнопка для температуры
    temp_button_text = localizer.format_value("settings-button-temperature", args={"value": temp_name})
    builder.button(text=temp_button_text, callback_data="settings:set:temperature")
    # Кнопка для макс. токенов
    tokens_button_text = localizer.format_value("settings-button-max-tokens", args={"value": tokens_name})
    builder.button(text=tokens_button_text, callback_data="settings:set:max_tokens")
    builder.adjust(1) # По кнопке в ряду
    return builder

# --- Обработчик команды /settings ---
@settings_router.message(Command("settings"))
async def handle_settings_command(message: types.Message, localizer: FluentLocalization):
    """Показывает текущие настройки и кнопки для их изменения."""
    user_id = message.from_user.id
    keyboard = await build_settings_keyboard(user_id, localizer)
    settings_text = localizer.format_value("settings-current-prompt")
    # Отправляем вместе с основной Reply клавиатурой
    main_reply_keyboard = get_main_keyboard(localizer)
    await message.answer(settings_text, reply_markup=keyboard.as_markup(), parse_mode=None) # Отключаем Markdown здесь

# --- Обработчик для возврата к главному меню настроек ---
@settings_router.callback_query(F.data == "settings:show")
async def cq_show_settings(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Показывает главный экран настроек (по нажатию кнопки 'Назад')."""
    user_id = callback.from_user.id
    keyboard = await build_settings_keyboard(user_id, localizer)
    settings_text = localizer.format_value("settings-current-prompt")
    try:
        # Редактируем предыдущее сообщение
        await callback.message.edit_text(settings_text, reply_markup=keyboard.as_markup(), parse_mode=None)
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения для показа настроек (user_id={user_id}): {e}")
    await callback.answer()

# --- Обработчик для выбора параметра для изменения ---
@settings_router.callback_query(F.data.startswith("settings:set:"))
async def cq_set_parameter(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Показывает опции для выбранного параметра."""
    try:
        parameter = callback.data.split(":")[2]
    except IndexError:
        logger.warning(f"Некорректный callback_data 'settings:set:': {callback.data}")
        await callback.answer("Ошибка!", show_alert=True)
        return

    user_id = callback.from_user.id
    current_temp, current_max_tokens = await get_user_settings(user_id) # Получаем текущие значения для отметки

    builder = InlineKeyboardBuilder()
    prompt_text = ""

    if parameter == "temperature":
        prompt_text = localizer.format_value("settings-prompt-temperature")
        # Добавляем кнопку для значения по умолчанию
        default_temp_text = localizer.format_value("settings-option-default", args={"value": f"{DEFAULT_GEMINI_TEMPERATURE:.1f}"})
        is_current = (current_temp == DEFAULT_GEMINI_TEMPERATURE)
        builder.button(
            text=f"✅ {default_temp_text}" if is_current else default_temp_text,
            callback_data=f"settings:value:temperature:{DEFAULT_GEMINI_TEMPERATURE}" # Передаем числовое значение
        )
        # Добавляем остальные опции
        for name, value in ALLOWED_TEMPERATURES.items():
            is_current = (abs(current_temp - value) < 0.01) # Сравнение float
            button_text = localizer.format_value(f"settings-option-temperature-{name}")
            builder.button(
                text=f"✅ {button_text}" if is_current else button_text,
                callback_data=f"settings:value:temperature:{value}"
            )

    elif parameter == "max_tokens":
        prompt_text = localizer.format_value("settings-prompt-max-tokens")
        # Кнопка для значения по умолчанию
        default_tokens_text = localizer.format_value("settings-option-default", args={"value": str(DEFAULT_GEMINI_MAX_TOKENS)})
        is_current = (current_max_tokens == DEFAULT_GEMINI_MAX_TOKENS)
        builder.button(
            text=f"✅ {default_tokens_text}" if is_current else default_tokens_text,
            callback_data=f"settings:value:max_tokens:{DEFAULT_GEMINI_MAX_TOKENS}" # Передаем числовое значение
        )
        # Остальные опции
        for name, value in ALLOWED_MAX_TOKENS.items():
            is_current = (current_max_tokens == value)
            button_text = localizer.format_value(f"settings-option-max-tokens-{name}")
            builder.button(
                text=f"✅ {button_text}" if is_current else button_text,
                callback_data=f"settings:value:max_tokens:{value}"
            )
    else:
        logger.warning(f"Неизвестный параметр в 'settings:set:': {parameter}")
        await callback.answer("Неизвестный параметр!", show_alert=True)
        return

    # Добавляем кнопку "Назад"
    back_button_text = localizer.format_value("button-back")
    builder.button(text=back_button_text, callback_data="settings:show")
    builder.adjust(1) # Все кнопки в один столбец для выбора значения

    try:
        await callback.message.edit_text(prompt_text, reply_markup=builder.as_markup(), parse_mode=None)
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения для установки параметра {parameter} (user_id={user_id}): {e}")
    await callback.answer()


# --- Обработчик для сохранения выбранного значения ---
@settings_router.callback_query(F.data.startswith("settings:value:"))
async def cq_save_value(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Сохраняет выбранное значение настройки и возвращает на главный экран настроек."""
    try:
        parts = callback.data.split(":")
        parameter = parts[2]
        value_str = parts[3]
    except IndexError:
        logger.warning(f"Некорректный callback_data 'settings:value:': {callback.data}")
        await callback.answer("Ошибка!", show_alert=True)
        return

    user_id = callback.from_user.id
    setting_saved = False
    db_field_name = ""
    final_value: Union[float, int, None] = None # Используем Union

    if parameter == "temperature":
        db_field_name = "gemini_temperature"
        try:
            final_value = float(value_str)
            # Проверка на допустимость (хотя кнопки должны генерировать только допустимые)
            allowed_values_list = list(ALLOWED_TEMPERATURES.values()) + [DEFAULT_GEMINI_TEMPERATURE]
            if not any(abs(final_value - v) < 0.01 for v in allowed_values_list):
                 raise ValueError("Value not in allowed list")
        except ValueError:
            logger.warning(f"Некорректное значение температуры '{value_str}' от user_id={user_id}")
            await callback.answer("Некорректное значение!", show_alert=True)
            return

    elif parameter == "max_tokens":
        db_field_name = "gemini_max_tokens"
        try:
            final_value = int(value_str)
            allowed_values_list = list(ALLOWED_MAX_TOKENS.values()) + [DEFAULT_GEMINI_MAX_TOKENS]
            if final_value not in allowed_values_list:
                raise ValueError("Value not in allowed list")
        except ValueError:
            logger.warning(f"Некорректное значение макс. токенов '{value_str}' от user_id={user_id}")
            await callback.answer("Некорректное значение!", show_alert=True)
            return
    else:
        logger.warning(f"Неизвестный параметр в 'settings:value:': {parameter}")
        await callback.answer("Неизвестный параметр!", show_alert=True)
        return

    # Сохраняем значение в БД
    if final_value is not None:
        setting_saved = await save_user_setting(user_id, db_field_name, final_value)

    if setting_saved:
        # Показываем обновленный главный экран настроек
        await cq_show_settings(callback, localizer) # Переиспользуем функцию
        # Не нужно делать answer здесь, так как он будет в cq_show_settings
    else:
        # Сообщаем об ошибке сохранения
        error_text = localizer.format_value("error-settings-save")
        await callback.answer(error_text, show_alert=True)