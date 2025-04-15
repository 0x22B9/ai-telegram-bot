from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from fluent.runtime import FluentLocalization
import logging

from src.localization import SUPPORTED_LOCALES, get_localizer, LOCALIZATIONS

# Создаем роутер для общих команд
common_router = Router()

@common_router.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """
    Обработчик команды /start. Предлагает выбрать язык.
    """
    await state.clear()

    builder = InlineKeyboardBuilder()
    for lang_code in SUPPORTED_LOCALES:
        lang_localizer = LOCALIZATIONS[lang_code]
        button_text = lang_localizer.format_value('language-select-button')
        builder.button(text=button_text, callback_data=f"lang_select:{lang_code}")
    builder.adjust(1)

    prompt_text = localizer.format_value('start-prompt')
    await message.answer(
        prompt_text,
        reply_markup=builder.as_markup()
    )

# --- Language Selection Callback ---
# ИСПОЛЬЗУЕМ ФИЛЬТР ПРЯМО В ДЕКОРАТОРЕ:
@common_router.callback_query(F.data.startswith("lang_select:"))
async def handle_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор языка из inline-кнопки.
    """
    # Убедимся, что работаем именно с CallbackQuery (хотя декоратор это уже гарантирует)
    if not isinstance(callback_query, types.CallbackQuery):
        return # На всякий случай

    await callback_query.answer()

    try:
        # callback_query.data гарантированно будет строкой, начинающейся с "lang_select:"
        lang_code = callback_query.data.split(":")[1]
    except (IndexError, AttributeError):
        # Если data некорректный, логируем и выходим
        logging.warning(f"Некорректный callback_data получен: {callback_query.data}")
        return

    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.full_name

    if lang_code not in SUPPORTED_LOCALES:
        logging.warning(f"Получен неподдерживаемый код языка: {lang_code} от user_id={user_id}")
        # Можно отправить сообщение об ошибке пользователю, если нужно
        return

    await state.update_data(language_code=lang_code)
    new_localizer = get_localizer(lang_code)
    welcome_message = new_localizer.format_value('language-chosen', args={"user_name": user_name})

    try:
        # Редактируем сообщение, если оно существует
        if callback_query.message:
             await callback_query.message.edit_text(
                 welcome_message,
                 reply_markup=None
             )
        else:
             # Если исходного сообщения нет (редко, но возможно), отправляем новое
             await callback_query.bot.send_message(chat_id=user_id, text=welcome_message)
    except Exception as e:
        logging.error(f"Ошибка при редактировании/отправке сообщения о выборе языка для user_id={user_id}: {e}")
        # Попытка отправить новое сообщение как фоллбэк
        try:
            await callback_query.bot.send_message(chat_id=user_id, text=welcome_message)
        except Exception as final_e:
            logging.error(f"Не удалось даже отправить новое сообщение о выборе языка для user_id={user_id}: {final_e}")

# --- Help Command ---
@common_router.message(Command("help"))
async def handle_help(message: types.Message, localizer: FluentLocalization):
    """
    Обработчик команды /help. Использует локализатор из middleware.
    """
    help_text = localizer.format_value('help-text')
    await message.answer(help_text) # parse_mode уже установлен в боте