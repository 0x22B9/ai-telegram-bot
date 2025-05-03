import asyncio
import logging

from aiogram import F, Router, types
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization

from src.db import delete_user_data
from src.services.errors import (
    TELEGRAM_MESSAGE_DELETED_ERROR,
    TELEGRAM_NETWORK_ERROR,
    format_error_message,
)

logger = logging.getLogger(__name__)
privacy_router = Router()

DELETE_DATA_PREFIX = "delete_my_data_confirm"


@privacy_router.message(Command("delete_my_data"))
async def handle_delete_my_data_command(
    message: types.Message, localizer: FluentLocalization
):
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
    try:
        await message.answer(confirmation_text, reply_markup=builder.as_markup())
    except Exception as e_send:
        logger.error(
            f"DeleteData: Could not send confirmation to user {message.from_user.id}: {e_send}"
        )


@privacy_router.callback_query(F.data.startswith(DELETE_DATA_PREFIX + ":"))
async def handle_delete_confirmation_callback(
    callback: types.CallbackQuery, localizer: FluentLocalization
):
    """Handles user confirmation to delete data."""
    user_id = callback.from_user.id
    action = callback.data.split(":")[-1]

    try:
        await callback.answer()
    except Exception as e_ans:
        logger.warning(
            f"DeleteData: Could not answer callback for user {user_id}: {e_ans}"
        )

    result_text = ""
    message_to_edit = callback.message

    if action == "yes":
        logger.warning(f"User user_id={user_id} confirmed data deletion.")
        deleted = False
        try:
            deleted = await delete_user_data(user_id)
        except Exception as e_db:
            logger.exception(
                f"DeleteData: Error deleting data for user {user_id} from DB: {e_db}"
            )
            result_text = localizer.format_value("delete-error")

        if not result_text:
            if deleted:
                result_text = localizer.format_value("delete-success")
                logger.info(f"Data for user_id={user_id} deleted successfully.")
            else:
                result_text = localizer.format_value("delete-not-found")
                logger.info(f"Data for user_id={user_id} not found for deletion.")

    elif action == "no":
        logger.info(f"User user_id={user_id} cancelled data deletion.")
        result_text = localizer.format_value("delete-cancelled")
    else:
        logger.error(
            f"Unknown action in delete callback: {callback.data} from user_id={user_id}"
        )
        result_text = localizer.format_value("error-general")

    if message_to_edit:
        try:
            await message_to_edit.edit_text(result_text, reply_markup=None)
        except TelegramRetryAfter as e:
            logger.warning(
                f"DeleteData: Flood control editing message for user {user_id}: retry after {e.retry_after}s"
            )
            await asyncio.sleep(e.retry_after)
            try:
                await message_to_edit.edit_text(result_text, reply_markup=None)
            except Exception:
                pass
        except TelegramBadRequest as e:
            if "message to edit not found" in str(e).lower():
                logger.warning(
                    f"DeleteData: Message {message_to_edit.message_id} not found. Sending new."
                )
                try:
                    await callback.bot.send_message(user_id, result_text)
                except Exception as send_e:
                    logger.error(
                        f"DeleteData: Failed send new message for user {user_id}: {send_e}"
                    )
            else:
                logger.error(
                    f"DeleteData: Error editing message for user {user_id}: {e}"
                )
        except TelegramNetworkError as e_net:
            logger.error(
                f"DeleteData: Network error editing message for user {user_id}: {e_net}"
            )
        except Exception as e_unexp:
            logger.error(
                f"DeleteData: Unexpected error editing message for user {user_id}: {e_unexp}",
                exc_info=True,
            )
    else:
        logger.warning(
            f"DeleteData: No message found in callback query for user {user_id}"
        )
        try:
            await callback.bot.send_message(user_id, result_text)
        except Exception as send_e:
            logger.error(
                f"DeleteData: Failed send message directly for user {user_id}: {send_e}"
            )
