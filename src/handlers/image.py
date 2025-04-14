import logging
import io
from aiogram import Router, types, F, Bot # Импортируем Bot для скачивания файла
from aiogram.fsm.context import FSMContext

from src.services import gemini

# Настройка логгирования
logger = logging.getLogger(__name__)

# Создаем роутер для изображений
image_router = Router()

@image_router.message(F.photo) # Ловим сообщения с фото
async def handle_image_message(message: types.Message, bot: Bot, state: FSMContext):
    """
    Обработчик сообщений с изображениями. Отправляет изображение в Gemini Vision.
    """
    user_id = message.from_user.id
    logger.info(f"Получено изображение от user_id={user_id}.")

    # Получаем объект фото самого большого размера
    photo = message.photo[-1]

    # Отправляем "Анализирую..."
    thinking_message = await message.answer("🖼️ Анализирую изображение...")

    # Скачиваем изображение в байты
    image_bytes_io = io.BytesIO()
    try:
        await bot.download(file=photo, destination=image_bytes_io)
        image_bytes = image_bytes_io.getvalue()
        logger.debug(f"Изображение от user_id={user_id} успешно скачано ({len(image_bytes)} байт).")
    except Exception as e:
        logger.error(f"Ошибка скачивания изображения от user_id={user_id}: {e}", exc_info=True)
        await thinking_message.edit_text("😔 Не удалось загрузить ваше изображение. Попробуйте еще раз.")
        return
    finally:
        image_bytes_io.close() # Закрываем BytesIO

    # Определяем промпт для Gemini
    # Если есть подпись к фото, используем ее. Иначе - просим описать изображение.
    prompt = message.caption if message.caption else "Опиши это изображение."
    logger.info(f"Промпт для Gemini Vision (user_id={user_id}): {prompt}")

    # Вызываем функцию Gemini для анализа изображения
    response_text = await gemini.analyze_image(image_bytes, prompt)

    if response_text:
        await thinking_message.edit_text(response_text)
        logger.info(f"Анализ изображения Gemini для user_id={user_id} завершен.")
    else:
        await thinking_message.edit_text("😔 Не удалось проанализировать изображение с помощью Gemini. Попробуйте позже.")
        logger.warning(f"Не удалось получить анализ изображения Gemini для user_id={user_id}.")