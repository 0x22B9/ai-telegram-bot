import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization
from aiogram.exceptions import TelegramBadRequest

from src.db import delete_user_data
from src.keyboards import get_main_keyboard

logger = logging.getLogger(__name__)
privacy_router = Router()

DELETE_DATA_PREFIX = "delete_my_data_confirm"

@privacy_router.message(Command("delete_my_data"))
async def handle_delete_my_data_command(message: types.Message, localizer: FluentLocalization):
    """Sends request to delete user data."""
    user_id = message.from_user.id
    logger.info(f"User user_id={user_id} requested to delete data.")

    builder = InlineKeyboardBuilder()
    yes_button_text = localizer.format_value("button-confirm-delete")
    no_button_text = localizer.format_value("button-cancel-delete")
    builder.button(text=yes_button_text, callback_data=f"{DELETE_DATA_PREFIX}:yes")
    builder.button(text=no_button_text, callback_data=f"{DELETE_DATA_PREFIX}:no")
    builder.adjust(2)

    confirmation_text = localizer.format_value("confirm-delete-prompt")
    await message.answer(
        confirmation_text,
        reply_markup=builder.as_markup()
    )

@privacy_router.callback_query(F.data.startswith(DELETE_DATA_PREFIX + ":"))
async def handle_delete_confirmation_callback(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Handles user confirmation to delete data."""
    user_id = callback.from_user.id
    action = callback.data.split(":")[-1]

    await callback.answer()

    if action == "yes":
        logger.warning(f"User user_id={user_id} confirmed to delete data.")
        deleted = await delete_user_data(user_id)

        if deleted:
            result_text = localizer.format_value("delete-success")
            logger.info(f"Data for user_id={user_id} deleted.")
        else:
            result_text = localizer.format_value("delete-error")
            logger.error(f"Can't delete data for user_id={user_id} after confirmation.")

        try:
            await callback.message.edit_text(result_text, reply_markup=None)
        except TelegramBadRequest as e:
            logger.warning(f"Can't edit message after confirmation for user_id={user_id}: {e}")
            if "message to edit not found" in str(e).lower():
                 main_kbd = get_main_keyboard(localizer)
                 await callback.message.answer(result_text, reply_markup=main_kbd)

    elif action == "no":
        logger.info(f"User user_id={user_id} cancelled to delete data.")
        result_text = localizer.format_value("delete-cancelled")
        try:
            await callback.message.edit_text(result_text, reply_markup=None)
        except TelegramBadRequest as e:
             logger.warning(f"Can't edit message after cancellation for user_id={user_id}: {e}")
             if "message to edit not found" in str(e).lower():
                  main_kbd = get_main_keyboard(localizer)
                  await callback.message.answer(result_text, reply_markup=main_kbd)

    else:
        logger.error(f"Unknown action in callback data: {callback.data} from user_id={user_id}")