import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from src.services import gemini

# Настройка логгирования
logger = logging.getLogger(__name__)

# Создаем роутер для текстовых сообщений
text_router = Router()

@text_router.message(F.text & ~F.text.startswith('/')) # Ловим все текстовые сообщения, кроме команд
async def handle_text_message(message: types.Message, state: FSMContext, bot: Bot): # Добавляем state на всякий случай
    """
    Обработчик текстовых сообщений. Отправляет текст в Gemini и отвечает пользователю.
    Обрабатывает возможные ошибки парсинга Markdown.
    """
    user_text = message.text
    user_id = message.from_user.id
    logger.info(f"Получено текстовое сообщение от user_id={user_id}: {user_text[:50]}...") # Логгируем начало сообщения

    # Отправляем "Думаю..."
    thinking_message = await message.answer("🧠 Думаю над вашим вопросом...")

    # Вызываем функцию Gemini для генерации текста
    response_text = await gemini.generate_text(user_text)

    if response_text:
        try:
            # Пытаемся отредактировать сообщение с использованием parse_mode по умолчанию (Markdown)
            await thinking_message.edit_text(response_text)
            logger.info(f"Ответ Gemini для user_id={user_id} сгенерирован (с форматированием).")
        except TelegramBadRequest as e:
            # Ловим ошибку, если Telegram не смог распарсить сущности (Markdown)
            if "can't parse entities" in str(e):
                logger.warning(f"Ошибка парсинга Markdown в ответе Gemini для user_id={user_id}. Попытка отправки без форматирования. Ошибка: {e}")
                try:
                    # Повторная попытка редактирования, но без parse_mode
                    await thinking_message.edit_text(response_text, parse_mode=None)
                    logger.info(f"Ответ Gemini для user_id={user_id} сгенерирован (без форматирования).")
                except Exception as fallback_e:
                    # Если и без форматирования не отправилось (маловероятно, но возможно)
                    logger.error(f"Не удалось отправить ответ Gemini даже без форматирования для user_id={user_id}: {fallback_e}", exc_info=True)
                    await thinking_message.edit_text("😔 Произошла ошибка при отображении ответа. Попробуйте позже.")
            else:
                # Если это другая ошибка BadRequest, логируем ее и сообщаем пользователю
                logger.error(f"Неожиданная ошибка TelegramBadRequest при отправке ответа Gemini для user_id={user_id}: {e}", exc_info=True)
                await thinking_message.edit_text("😔 Произошла ошибка при отправке ответа. Попробуйте позже.")
        except Exception as e:
            # Ловим другие возможные ошибки при редактировании
            logger.error(f"Общая ошибка при редактировании сообщения с ответом Gemini для user_id={user_id}: {e}", exc_info=True)
            await thinking_message.edit_text("😔 Произошла ошибка при обработке ответа. Попробуйте позже.")
    else:
        # Если Gemini вернул None или пустую строку (из-за ошибки)
        await thinking_message.edit_text("😔 Не удалось получить ответ от Gemini. Попробуйте позже.")
        logger.warning(f"Не удалось получить ответ Gemini для user_id={user_id}.")