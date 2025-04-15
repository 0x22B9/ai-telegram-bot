import logging
import io
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest # Добавлен импорт для обработки ошибок парсинга ответа
from fluent.runtime import FluentLocalization # Импорт

from src.services import gemini

# Настройка логгирования
logger = logging.getLogger(__name__)

# Создаем роутер для изображений
image_router = Router()

@image_router.message(F.photo)
# Добавляем localizer
async def handle_image_message(message: types.Message, bot: Bot, state: FSMContext, localizer: FluentLocalization):
    user_id = message.from_user.id
    logger.info(f"Получено изображение от user_id={user_id} ({localizer.locales[0]}).")

    photo = message.photo[-1]

    # Используем локализованную строку
    analyzing_text = localizer.format_value('analyzing')
    thinking_message = await message.answer(analyzing_text)

    image_bytes_io = io.BytesIO()
    try:
        await bot.download(file=photo, destination=image_bytes_io)
        image_bytes = image_bytes_io.getvalue()
        logger.debug(f"Изображение от user_id={user_id} скачано ({len(image_bytes)} байт).")
    except Exception as e:
        logger.error(f"Ошибка скачивания изображения от user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-image-download')
        await thinking_message.edit_text(error_msg)
        return
    finally:
        image_bytes_io.close()

    prompt = message.caption if message.caption else "Опиши это изображение." # Этот промпт идет в Gemini, его не локализуем, если он от пользователя
    logger.info(f"Промпт для Gemini Vision (user_id={user_id}): {prompt}")

    response_text = await gemini.analyze_image(image_bytes, prompt)

    if response_text:
        # Локализация сообщений об ошибках от Gemini
        if response_text == "Ошибка: Ключ Gemini API не настроен.":
             error_msg = localizer.format_value('error-gemini-api-key')
             await thinking_message.edit_text(error_msg)
             return
        if response_text.startswith("Мой ответ на изображение был заблокирован"):
             reason = "Unknown"
             try:
                 start_index = response_text.find("(Причина: ") + len("(Причина: ")
                 end_index = response_text.find(")")
                 if start_index != -1 and end_index != -1:
                     reason = response_text[start_index:end_index]
             except Exception: pass
             error_msg = localizer.format_value('error-blocked-image-content', args={'reason': reason})
             await thinking_message.edit_text(error_msg)
             return
        if response_text.startswith("Произошла ошибка при анализе изображения:"):
             error_detail = response_text.split(":", 1)[1].strip()
             error_msg = localizer.format_value('error-image-analysis-request', args={'error': error_detail})
             await thinking_message.edit_text(error_msg)
             return

        # Отправка ответа с обработкой ошибок парсинга (аналогично текстовому хэндлеру)
        try:
            await thinking_message.edit_text(response_text)
            logger.info(f"Анализ изображения Gemini для user_id={user_id} завершен.")
        except TelegramBadRequest as e:
            if "can't parse entities" in str(e):
                logger.warning(f"Ошибка парсинга HTML (Vision) для user_id={user_id}. Отправка без форматирования. Ошибка: {e}")
                try:
                    await thinking_message.edit_text(response_text, parse_mode=None)
                except Exception as fallback_e:
                    logger.error(f"Не удалось отправить ответ (Vision) даже без форматирования для user_id={user_id}: {fallback_e}", exc_info=True)
                    error_msg = localizer.format_value('error-display')
                    await thinking_message.edit_text(error_msg)
            else:
                 logger.error(f"Неожиданная ошибка TelegramBadRequest (Vision) для user_id={user_id}: {e}", exc_info=True)
                 error_msg = localizer.format_value('error-general')
                 await thinking_message.edit_text(error_msg)
        except Exception as e:
            logger.error(f"Общая ошибка при редактировании сообщения (Vision) для user_id={user_id}: {e}", exc_info=True)
            error_msg = localizer.format_value('error-general')
            await thinking_message.edit_text(error_msg)

    else:
        error_msg = localizer.format_value('error-image-analysis')
        await thinking_message.edit_text(error_msg)
        logger.warning(f"Не удалось получить анализ изображения Gemini для user_id={user_id}.")