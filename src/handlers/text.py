import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext # Может понадобиться для сложных диалогов

from src.services import gemini # Импортируем наш модуль для работы с Gemini

# Настройка логгирования
logger = logging.getLogger(__name__)

# Создаем роутер для текстовых сообщений
text_router = Router()

@text_router.message(F.text & ~F.text.startswith('/')) # Ловим все текстовые сообщения, кроме команд
async def handle_text_message(message: types.Message, state: FSMContext): # Добавляем state на всякий случай
    """
    Обработчик текстовых сообщений. Отправляет текст в Gemini и отвечает пользователю.
    """
    user_text = message.text
    user_id = message.from_user.id
    logger.info(f"Получено текстовое сообщение от user_id={user_id}: {user_text[:50]}...") # Логгируем начало сообщения

    # Отправляем "Думаю..."
    thinking_message = await message.answer("🧠 Думаю над вашим вопросом...")

    # Вызываем функцию Gemini для генерации текста
    response_text = await gemini.generate_text(user_text)

    if response_text:
        # Редактируем сообщение "Думаю..." на ответ от Gemini
        await thinking_message.edit_text(response_text)
        logger.info(f"Ответ Gemini для user_id={user_id} сгенерирован.")
    else:
        # Если Gemini вернул None или пустую строку (из-за ошибки)
        await thinking_message.edit_text("😔 Не удалось получить ответ от Gemini. Попробуйте позже.")
        logger.warning(f"Не удалось получить ответ Gemini для user_id={user_id}.")