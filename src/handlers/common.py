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
    Проверяет, выбран ли язык. Если нет - предлагает выбор. Если да - приветствует.
    """
    user_data = await state.get_data()
    current_lang_code = user_data.get("language_code")
    user_name = message.from_user.full_name

    if current_lang_code and current_lang_code in SUPPORTED_LOCALES:
        # Язык уже выбран, просто приветствуем на выбранном языке
        # localizer уже будет правильным благодаря middleware
        welcome_message = localizer.format_value('start-welcome', args={"user_name": user_name})
        await message.answer(welcome_message)
    else:
        # Язык не выбран или некорректен, предлагаем выбрать
        await state.clear() # Очищаем состояние перед выбором языка
        # localizer здесь будет дефолтным или тем, что определился до state
        await send_language_selection_message(message, get_localizer()) # Отправляем с дефолтным локализатором

# --- Language Command ---
@common_router.message(Command("language"))
async def handle_language_command(message: types.Message, localizer: FluentLocalization):
    """
    Обработчик команды /language. Всегда предлагает сменить язык.
    """
    # localizer будет текущим языком пользователя, используем его для промпта
    await send_language_selection_message(message, localizer)

# --- Language Selection Callback ---
@common_router.callback_query(F.data.startswith("lang_select:"))
async def handle_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор языка из inline-кнопки (от /start или /language).
    """
    if not isinstance(callback_query, types.CallbackQuery) or not callback_query.data:
        return

    await callback_query.answer() # Убираем часики

    try:
        lang_code = callback_query.data.split(":")[1]
    except IndexError:
        logging.warning(f"Некорректный callback_data 'lang_select': {callback_query.data}")
        return

    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.full_name

    if lang_code not in SUPPORTED_LOCALES:
        logging.warning(f"Получен неподдерживаемый код языка: {lang_code} от user_id={user_id}")
        return

    # Сохраняем выбранный язык в FSM storage
    await state.update_data(language_code=lang_code)
    logging.info(f"User {user_id} chose language: {lang_code}") # Логируем смену языка

    # Получаем локализатор для ВЫБРАННОГО языка
    new_localizer = get_localizer(lang_code)

    # Формируем сообщение о смене языка на выбранном языке
    welcome_message = new_localizer.format_value('language-chosen', args={"user_name": user_name})

    # Редактируем исходное сообщение (с кнопками выбора языка)
    try:
        if callback_query.message:
            await callback_query.message.edit_text(
                welcome_message,
                reply_markup=None # Убираем клавиатуру
            )
        else:
            # Если исходного сообщения нет, отправляем новое
            await callback_query.bot.send_message(chat_id=user_id, text=welcome_message)
    except Exception as e:
        logging.error(f"Ошибка при редактировании/отправке сообщения о выборе языка для user_id={user_id}: {e}")
        # Фоллбэк: отправить новое сообщение, если редактирование не удалось
        try:
            await callback_query.bot.send_message(chat_id=user_id, text=welcome_message)
        except Exception as final_e:
            logging.error(f"Не удалось даже отправить новое сообщение о выборе языка для user_id={user_id}: {final_e}")

@common_router.message(Command("model"))
async def handle_model_command(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """
    Обработчик команды /model. Предлагает выбрать модель Gemini для текста.
    """
    builder = InlineKeyboardBuilder()
    user_data = await state.get_data()
    current_model = user_data.get("selected_model") # Получаем текущую выбранную модель

    for model_name in AVAILABLE_TEXT_MODELS:
        # Добавляем отметку к текущей модели
        button_text = f"✅ {model_name}" if model_name == current_model else model_name
        builder.button(
            text=button_text,
            callback_data=f"model_select:{model_name}"
        )
    builder.adjust(1) # По одной кнопке в ряду

    prompt_text = localizer.format_value('model-prompt')
    await message.answer(prompt_text, reply_markup=builder.as_markup())

@common_router.callback_query(F.data.startswith("model_select:"))
async def handle_model_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор модели из inline-кнопки.
    Отправляет подтверждение новым сообщением и удаляет исходное сообщение с кнопками.
    """
    if not isinstance(callback_query, types.CallbackQuery) or not callback_query.data:
        return

    # Сразу отвечаем на колбэк, чтобы убрать часики
    await callback_query.answer()

    try:
        selected_model = callback_query.data.split(":")[1]
    except IndexError:
        logging.warning(f"Некорректный callback_data 'model_select': {callback_query.data}")
        return

    user_id = callback_query.from_user.id

    if selected_model not in AVAILABLE_TEXT_MODELS:
        logging.warning(f"Получена неподдерживаемая модель: {selected_model} от user_id={user_id}")
        # Можно уведомить пользователя об ошибке, если нужно
        return

    # Сохраняем выбранную модель в FSM storage
    await state.update_data(selected_model=selected_model)
    logging.info(f"User {user_id} chose model: {selected_model}")

    # Получаем локализатор для текущего языка пользователя
    user_data = await state.get_data()
    lang_code = user_data.get("language_code")
    current_localizer = get_localizer(lang_code) # Важно использовать текущий язык для ответа

    # Формируем сообщение о смене модели
    response_text = current_localizer.format_value('model-chosen', args={"model_name": selected_model})

    # --- Логика изменена: Отправка нового сообщения и удаление старого ---
    try:
        # 1. Отправляем новое сообщение с подтверждением
        # Используем message.answer для ответа в том же чате
        if callback_query.message: # Убедимся что исходное сообщение существует
            await callback_query.message.answer(response_text)
        else: # Редкий случай, если исходного сообщения почему-то нет
            await callback_query.bot.send_message(chat_id=user_id, text=response_text)

        # 2. Удаляем исходное сообщение с кнопками
        if callback_query.message:
            await callback_query.message.delete()
            logging.debug(f"Сообщение с выбором модели ({callback_query.message.message_id}) удалено для user_id={user_id}.")

    except TelegramBadRequest as e:
        # Ловим ошибку, если сообщение не может быть удалено (например, слишком старое)
        if "message to delete not found" in str(e) or "message can't be deleted" in str(e):
            logger.warning(f"Не удалось удалить сообщение с выбором модели для user_id={user_id}: {e}")
        else:
            # Другие возможные ошибки при отправке/удалении
            logger.error(f"Ошибка при отправке подтверждения/удалении сообщения выбора модели для user_id={user_id}: {e}")
            # Если удаление не удалось, подтверждение уже отправлено (или была ошибка выше)
    except Exception as e:
         # Ловим другие неожиданные ошибки
         logger.error(f"Неожиданная ошибка при отправке/удалении сообщения выбора модели для user_id={user_id}: {e}", exc_info=True)
         # Попытка отправить подтверждение, если оно не было отправлено из-за ошибки выше
         if callback_query.message: # Проверяем снова на всякий случай
            try:
                 await callback_query.message.answer(response_text)
            except Exception as final_e:
                 logging.error(f"Не удалось даже отправить сообщение о выборе модели для user_id={user_id}: {final_e}")

# --- New Chat Command --- Добавлено ---
@common_router.message(Command("newchat"))
async def handle_new_chat(message: types.Message, localizer: FluentLocalization):
    """
    Обработчик команды /newchat. Очищает историю чата пользователя.
    """
    user_id = message.from_user.id
    success = await clear_history(user_id)

    if success:
        response_text = localizer.format_value("newchat-started")
        logger.info(f"Пользователь {user_id} начал новый чат.")
    else:
        response_text = localizer.format_value("error-general") # Общая ошибка, если очистка не удалась
        logger.error(f"Не удалось очистить историю для пользователя {user_id}.")

    await message.answer(response_text)

# --- Help Command ---
@common_router.message(Command("help"))
async def handle_help(message: types.Message, localizer: FluentLocalization):
    """
    Обработчик команды /help. Использует локализатор из middleware.
    """
    # Убедимся, что добавили /language в текст помощи в .ftl файлах
    help_text = localizer.format_value('help-text')
    await message.answer(help_text)