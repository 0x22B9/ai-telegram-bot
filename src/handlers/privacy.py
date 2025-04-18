# src/handlers/privacy.py
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization
from aiogram.exceptions import TelegramBadRequest

# Импортируем функцию удаления из db
from src.db import delete_user_data
from src.keyboards import get_main_keyboard # Для восстановления клавиатуры после отмены

logger = logging.getLogger(__name__)
privacy_router = Router()

# Префикс для callback_data, чтобы избежать конфликтов
DELETE_DATA_PREFIX = "delete_my_data_confirm"

# Обработчик команды /delete_my_data
@privacy_router.message(Command("delete_my_data"))
async def handle_delete_my_data_command(message: types.Message, localizer: FluentLocalization):
    """Отправляет запрос на подтверждение удаления данных."""
    user_id = message.from_user.id
    logger.info(f"Пользователь user_id={user_id} запросил удаление своих данных.")

    # Создаем клавиатуру подтверждения
    builder = InlineKeyboardBuilder()
    yes_button_text = localizer.format_value("button-confirm-delete")
    no_button_text = localizer.format_value("button-cancel-delete")
    builder.button(text=yes_button_text, callback_data=f"{DELETE_DATA_PREFIX}:yes")
    builder.button(text=no_button_text, callback_data=f"{DELETE_DATA_PREFIX}:no")
    builder.adjust(2) # Две кнопки в ряд

    confirmation_text = localizer.format_value("confirm-delete-prompt")
    await message.answer(
        confirmation_text,
        reply_markup=builder.as_markup()
    )

# Обработчик нажатия на кнопки подтверждения/отмены
@privacy_router.callback_query(F.data.startswith(DELETE_DATA_PREFIX + ":"))
async def handle_delete_confirmation_callback(callback: types.CallbackQuery, localizer: FluentLocalization):
    """Обрабатывает подтверждение или отмену удаления данных."""
    user_id = callback.from_user.id
    action = callback.data.split(":")[-1] # Получаем 'yes' или 'no'

    await callback.answer() # Отвечаем на коллбэк, чтобы убрать "часики"

    if action == "yes":
        logger.warning(f"Пользователь user_id={user_id} подтвердил удаление данных.")
        deleted = await delete_user_data(user_id)

        if deleted:
            result_text = localizer.format_value("delete-success")
            logger.info(f"Данные для user_id={user_id} удалены по подтверждению.")
        else:
            result_text = localizer.format_value("delete-error")
            logger.error(f"Не удалось удалить данные для user_id={user_id} после подтверждения.")

        try:
            # Редактируем исходное сообщение, убирая кнопки
            await callback.message.edit_text(result_text, reply_markup=None)
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение после удаления данных для user_id={user_id}: {e}")
            # Если сообщение не найдено, отправляем новое
            if "message to edit not found" in str(e).lower():
                 main_kbd = get_main_keyboard(localizer)
                 await callback.message.answer(result_text, reply_markup=main_kbd)

    elif action == "no":
        logger.info(f"Пользователь user_id={user_id} отменил удаление данных.")
        result_text = localizer.format_value("delete-cancelled")
        try:
            # Редактируем исходное сообщение, убирая кнопки
            await callback.message.edit_text(result_text, reply_markup=None)
        except TelegramBadRequest as e:
             logger.warning(f"Не удалось отредактировать сообщение после отмены удаления для user_id={user_id}: {e}")
             if "message to edit not found" in str(e).lower():
                  main_kbd = get_main_keyboard(localizer)
                  await callback.message.answer(result_text, reply_markup=main_kbd)

    else:
        logger.error(f"Неизвестное действие в коллбэке удаления данных: {callback.data} от user_id={user_id}")
        # Можно просто проигнорировать или сообщить об ошибке