from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from fluent.runtime import FluentLocalization
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
import logging

from src.localization import SUPPORTED_LOCALES, get_localizer, LOCALIZATIONS
from src.db import clear_history
from src.config import AVAILABLE_TEXT_MODELS, DEFAULT_TEXT_MODEL
from src.keyboards import get_main_keyboard
from src.services.errors import format_error_message, DATABASE_SAVE_ERROR, TELEGRAM_MESSAGE_DELETED_ERROR

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
        await callback_query.bot.send_message(chat_id=user_id, text=welcome_message, reply_markup=keyboard)
        if callback_query.message:
            try:
                await callback_query.message.delete()
            except TelegramBadRequest as e_del:
                 if "message to delete not found" in str(e_del).lower():
                      logger.warning(f"Lang select: Message {callback_query.message.message_id} already deleted.")
                 else:
                      logger.error(f"Lang select: Error deleting message {callback_query.message.message_id}: {e_del}")
            except TelegramNetworkError as e_net:
                 logger.error(f"Lang select: Network error deleting message: {e_net}")
            except Exception as e_unexp:
                 logger.error(f"Lang select: Unexpected error deleting message: {e_unexp}", exc_info=True)

    except (TelegramNetworkError, TelegramBadRequest) as e_send:
        logger.error(f"Lang select: Error sending welcome message for user {user_id}: {e_send}")
    except Exception as e_unexp_send:
         logger.error(f"Lang select: Unexpected error sending welcome message for user {user_id}: {e_unexp_send}", exc_info=True)


@common_router.message(Command("model"))
async def handle_model_command(message: types.Message, state: FSMContext, localizer: FluentLocalization):
    """/model command handler. Allows user to select a model for text generation."""
    builder = InlineKeyboardBuilder()
    user_data = await state.get_data()
    current_model = user_data.get("selected_model", DEFAULT_TEXT_MODEL)

    for model_name in AVAILABLE_TEXT_MODELS:
        button_text = f"✅ {model_name}" if model_name == current_model else model_name
        builder.button(text=button_text, callback_data=f"model_select:{model_name}")
    builder.adjust(1)

    prompt_text = localizer.format_value('model-prompt')
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
        await callback_query.bot.send_message(chat_id=user_id, text=response_text)

        if callback_query.message:
            try:
                await callback_query.message.delete()
            except TelegramBadRequest as e_del:
                 if "message to delete not found" in str(e_del).lower():
                      logger.warning(f"Model select: Message {callback_query.message.message_id} already deleted.")
                 else:
                      logger.error(f"Model select: Error deleting message {callback_query.message.message_id}: {e_del}")
            except TelegramNetworkError as e_net:
                 logger.error(f"Model select: Network error deleting message: {e_net}")
            except Exception as e_unexp:
                 logger.error(f"Model select: Unexpected error deleting message: {e_unexp}", exc_info=True)

    except (TelegramNetworkError, TelegramBadRequest) as e_send:
         logger.error(f"Model select: Error sending confirmation for user {user_id}: {e_send}")
    except Exception as e_unexp_send:
         logger.error(f"Model select: Unexpected error sending confirmation for user {user_id}: {e_unexp_send}", exc_info=True)
        

@common_router.message(Command("newchat"))
async def handle_new_chat(message: types.Message, localizer: FluentLocalization):
    """/newchat command handler. Clears the user's chat history."""
    user_id = message.from_user.id
    keyboard = get_main_keyboard(localizer)
    success = await clear_history(user_id)

    try:
        success = await clear_history(user_id)
        if success:
            response_text = localizer.format_value("newchat-started")
            logger.info(f"User {user_id} started a new chat.")
        else:
            response_text, _ = format_error_message(DATABASE_SAVE_ERROR, localizer)
            logger.error(f"Failed to clear history (clear_history returned False) for user {user_id}.")

    except Exception as e:
         logger.exception(f"Unexpected error during /newchat for user {user_id}: {e}")
         response_text, _ = format_error_message(None, localizer)

    try:
         await message.answer(response_text, reply_markup=keyboard)
    except Exception as e_send:
          logger.error(f"NewChat: Could not send response to user {user_id}: {e_send}")


@common_router.message(Command("help"))
async def handle_help(message: types.Message, localizer: FluentLocalization):
    """/help command handler."""
    help_text = localizer.format_value('help-text')
    keyboard = get_main_keyboard(localizer)
    try:
         await message.answer(help_text, reply_markup=keyboard)
    except Exception as e_send:
         logger.error(f"Help: Could not send help message to user {message.from_user.id}: {e_send}")