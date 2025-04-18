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

common_router = Router()
logger = logging.getLogger(__name__)

async def send_language_selection_message(message: types.Message, localizer: FluentLocalization):
    """Sends a message with language selection buttons."""
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

@common_router.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """ /start command handler. Initiates language selection or greets user."""
    user_data = await state.get_data()
    current_lang_code = user_data.get("language_code")
    user_name = message.from_user.full_name

    if current_lang_code and current_lang_code in SUPPORTED_LOCALES:
        welcome_message = localizer.format_value('start-welcome', args={"user_name": user_name})
        keyboard = get_main_keyboard(localizer)
        await message.answer(welcome_message, reply_markup=keyboard)
    else:
        await state.clear()
        await send_language_selection_message(message, get_localizer())

@common_router.message(Command("language"))
async def handle_language_command(message: types.Message, localizer: FluentLocalization):
    """/language command handler. Allows user to change bot UI language."""
    await send_language_selection_message(message, localizer)

@common_router.callback_query(F.data.startswith("lang_select:"))
async def handle_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Processes language selection. Sends a confirmation message and shows the main keyboard."""
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
        keyboard = get_main_keyboard(new_localizer)
        if callback_query.message:
            await callback_query.message.answer(welcome_message, reply_markup=keyboard)
        else:
            await callback_query.bot.send_message(chat_id=user_id, text=welcome_message, reply_markup=keyboard)

        if callback_query.message:
            await callback_query.message.delete()

    except TelegramBadRequest as e:
        logger.error(f"Error while sending/deleting message for user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while sending/deleting message for user_id={user_id}: {e}", exc_info=True)

@common_router.message(Command("model"))
async def handle_model_command(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """/model command handler. Allows user to select a model for text generation."""
    builder = InlineKeyboardBuilder()
    user_data = await state.get_data()
    current_model = user_data.get("selected_model")

    for model_name in AVAILABLE_TEXT_MODELS:
        button_text = f"✅ {model_name}" if model_name == current_model else model_name
        builder.button(text=button_text, callback_data=f"model_select:{model_name}")
    builder.adjust(1)

    prompt_text = localizer.format_value('model-prompt')
    keyboard = get_main_keyboard(localizer)
    await message.answer(prompt_text, reply_markup=builder.as_markup())

@common_router.callback_query(F.data.startswith("model_select:"))
async def handle_model_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Handles model selection. Updates the state and sends a confirmation message."""
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
        if callback_query.message:
             await callback_query.message.answer(response_text)
        else:
             await callback_query.bot.send_message(chat_id=user_id, text=response_text)

        if callback_query.message:
            await callback_query.message.delete()

    except TelegramBadRequest as e:
        logger.error(f"Error while sending/deleting message for user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while sending/deleting message for user_id={user_id}: {e}", exc_info=True)
        
@common_router.message(Command("newchat"))
async def handle_new_chat(message: types.Message, localizer: FluentLocalization):
    """/newchat command handler. Clears the user's chat history."""
    user_id = message.from_user.id
    success = await clear_history(user_id)

    if success:
        response_text = localizer.format_value("newchat-started")
        logger.info(f"User {user_id} started a new chat.")
    else:
        response_text = localizer.format_value("error-general")
        logger.error(f"Can't start a new chat for user {user_id}.")

    keyboard = get_main_keyboard(localizer)
    await message.answer(response_text, reply_markup=keyboard)

@common_router.message(Command("help"))
async def handle_help(message: types.Message, localizer: FluentLocalization):
    """/help command handler. Sends a help message."""
    help_text = localizer.format_value('help-text')
    keyboard = get_main_keyboard(localizer)
    await message.answer(help_text, reply_markup=keyboard)