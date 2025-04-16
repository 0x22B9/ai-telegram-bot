from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from fluent.runtime import FluentLocalization
from aiogram.exceptions import TelegramBadRequest
import logging

from src.localization import SUPPORTED_LOCALES, get_localizer, LOCALIZATIONS
from src.db import clear_history
from src.config import AVAILABLE_TEXT_MODELS
from src.keyboards import get_main_keyboard

# Создаем роутер для общих команд
common_router = Router()
logger = logging.getLogger(__name__)

# Вспомогательная функция для отправки сообщения с выбором языка
async def send_language_selection_message(message: types.Message, localizer: FluentLocalization):
    """Отправляет сообщение с кнопками выбора языка."""
    builder = InlineKeyboardBuilder()
    for lang_code in SUPPORTED_LOCALES:
        lang_localizer = LOCALIZATIONS[lang_code]
        button_text = lang_localizer.format_value('language-select-button')
        builder.button(text=button_text, callback_data=f"lang_select:{lang_code}")
    builder.adjust(1)

    prompt_text = localizer.format_value('start-prompt') # Используем 'start-prompt' для универсальности
    await message.answer(
        prompt_text,
        reply_markup=builder.as_markup()
    )

@common_router.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """
    Обработчик команды /start.
    Предлагает выбор языка или приветствует с главной клавиатурой.
    """
    user_data = await state.get_data()
    current_lang_code = user_data.get("language_code")
    user_name = message.from_user.full_name

    if current_lang_code and current_lang_code in SUPPORTED_LOCALES:
        # Язык уже выбран, приветствуем и показываем ГЛАВНУЮ КЛАВИАТУРУ
        welcome_message = localizer.format_value('start-welcome', args={"user_name": user_name})
        # Получаем и отправляем клавиатуру
        keyboard = get_main_keyboard(localizer)
        await message.answer(welcome_message, reply_markup=keyboard)
    else:
        # Язык не выбран, предлагаем выбрать (inline keyboard)
        await state.clear()
        await send_language_selection_message(message, get_localizer())

# --- Language Command ---
@common_router.message(Command("language"))
async def handle_language_command(message: types.Message, localizer: FluentLocalization):
    """
    Обработчик команды /language. Предлагает сменить язык И показывает главную клавиатуру.
    """
    # Отправляем inline-клавиатуру для выбора языка
    await send_language_selection_message(message, localizer)
    # Примечание: Основная клавиатура останется видимой после выбора языка

# --- Language Selection Callback ---
@common_router.callback_query(F.data.startswith("lang_select:"))
async def handle_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор языка. Отправляет подтверждение и ГЛАВНУЮ КЛАВИАТУРУ.
    """
    if not isinstance(callback_query, types.CallbackQuery) or not callback_query.data: return
    await callback_query.answer()

    try: lang_code = callback_query.data.split(":")[1]
    except IndexError: return

    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.full_name
    if lang_code not in SUPPORTED_LOCALES: return

    await state.update_data(language_code=lang_code)
    logging.info(f"User {user_id} chose language: {lang_code}")

    new_localizer = get_localizer(lang_code)
    welcome_message = new_localizer.format_value('language-chosen', args={"user_name": user_name})

    try:
        # 1. Отправляем новое сообщение с подтверждением И ГЛАВНОЙ КЛАВИАТУРОЙ
        keyboard = get_main_keyboard(new_localizer) # <<< Получаем клавиатуру
        if callback_query.message:
            await callback_query.message.answer(welcome_message, reply_markup=keyboard) # <<< Отправляем с клавиатурой
        else:
            await callback_query.bot.send_message(chat_id=user_id, text=welcome_message, reply_markup=keyboard)

        # 2. Удаляем старое сообщение с inline-кнопками
        if callback_query.message:
            await callback_query.message.delete()

    except TelegramBadRequest as e:
        # ... (обработка ошибок удаления/отправки) ...
        logger.error(f"Ошибка при отправке/удалении сообщения выбора языка для user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке/удалении сообщения выбора языка для user_id={user_id}: {e}", exc_info=True)

@common_router.message(Command("model"))
async def handle_model_command(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """
    Обработчик команды /model. Предлагает выбрать модель И показывает главную клавиатуру.
    """
    builder = InlineKeyboardBuilder()
    user_data = await state.get_data()
    current_model = user_data.get("selected_model")

    for model_name in AVAILABLE_TEXT_MODELS:
        button_text = f"✅ {model_name}" if model_name == current_model else model_name
        builder.button(text=button_text, callback_data=f"model_select:{model_name}")
    builder.adjust(1)

    prompt_text = localizer.format_value('model-prompt')
    # Показываем основную клавиатуру вместе с inline-кнопками выбора модели
    keyboard = get_main_keyboard(localizer)
    await message.answer(prompt_text, reply_markup=builder.as_markup())
    # Примечание: Основная клавиатура останется видимой после выбора модели

@common_router.callback_query(F.data.startswith("model_select:"))
async def handle_model_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор модели. Отправляет подтверждение И оставляет главную клавиатуру.
    """
    if not isinstance(callback_query, types.CallbackQuery) or not callback_query.data: return
    await callback_query.answer()

    try: selected_model = callback_query.data.split(":")[1]
    except IndexError: return

    user_id = callback_query.from_user.id
    if selected_model not in AVAILABLE_TEXT_MODELS: return

    await state.update_data(selected_model=selected_model)
    logging.info(f"User {user_id} chose model: {selected_model}")

    user_data = await state.get_data()
    lang_code = user_data.get("language_code")
    current_localizer = get_localizer(lang_code)

    response_text = current_localizer.format_value('model-chosen', args={"model_name": selected_model})

    try:
        # 1. Отправляем новое сообщение с подтверждением (основная клавиатура уже должна быть)
        if callback_query.message:
             await callback_query.message.answer(response_text) # Основная клавиатура не указывается, т.к. она уже есть
        else:
             await callback_query.bot.send_message(chat_id=user_id, text=response_text)

        # 2. Удаляем сообщение с inline-кнопками выбора модели
        if callback_query.message:
            await callback_query.message.delete()

    except TelegramBadRequest as e:
        # ... (обработка ошибок) ...
        logger.error(f"Ошибка при отправке/удалении сообщения выбора модели для user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке/удалении сообщения выбора модели для user_id={user_id}: {e}", exc_info=True)
        
# --- New Chat Command --- Добавлено ---
@common_router.message(Command("newchat"))
async def handle_new_chat(message: types.Message, localizer: FluentLocalization):
    """
    Обработчик команды /newchat. Очищает историю И показывает главную клавиатуру.
    """
    user_id = message.from_user.id
    success = await clear_history(user_id)

    if success:
        response_text = localizer.format_value("newchat-started")
        logger.info(f"Пользователь {user_id} начал новый чат.")
    else:
        response_text = localizer.format_value("error-general")
        logger.error(f"Не удалось очистить историю для пользователя {user_id}.")

    # Показываем основную клавиатуру
    keyboard = get_main_keyboard(localizer)
    await message.answer(response_text, reply_markup=keyboard)

# --- Help Command ---
@common_router.message(Command("help"))
async def handle_help(message: types.Message, localizer: FluentLocalization):
    """
    Обработчик команды /help. Показывает справку И главную клавиатуру.
    """
    help_text = localizer.format_value('help-text')
    # Показываем основную клавиатуру
    keyboard = get_main_keyboard(localizer)
    await message.answer(help_text, reply_markup=keyboard)