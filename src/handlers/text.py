import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from fluent.runtime import FluentLocalization # Импорт

from src.services import gemini

# Настройка логгирования
logger = logging.getLogger(__name__)

# Создаем роутер для текстовых сообщений
text_router = Router()

@text_router.message(F.text & ~F.text.startswith('/'))
# Добавляем localizer в параметры
async def handle_text_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    user_text = message.text
    user_id = message.from_user.id
    logger.info(f"Получено текстовое сообщение от user_id={user_id} ({localizer.locales[0]}): {user_text[:50]}...")

    # Используем локализованную строку
    thinking_text = localizer.format_value('thinking')
    thinking_message = await message.answer(thinking_text)

    response_text = await gemini.generate_text(user_text)

    if response_text:
        # Проверяем ошибки API ключа или блокировки контента и используем локализованные сообщения
        if response_text == "Ошибка: Ключ Gemini API не настроен.":
             error_msg = localizer.format_value('error-gemini-api-key')
             await thinking_message.edit_text(error_msg)
             return
        if response_text.startswith("Мой ответ был заблокирован"):
             # Извлекаем причину, если она есть (улучшенная версия)
             reason = "Unknown"
             try:
                 start_index = response_text.find("(Причина: ") + len("(Причина: ")
                 end_index = response_text.find(")")
                 if start_index != -1 and end_index != -1:
                     reason = response_text[start_index:end_index]
             except Exception: pass # Оставляем Unknown если не получилось
             error_msg = localizer.format_value('error-blocked-content', args={'reason': reason})
             await thinking_message.edit_text(error_msg)
             return
        if response_text.startswith("Произошла ошибка при обращении к Gemini:"):
             error_detail = response_text.split(":", 1)[1].strip()
             error_msg = localizer.format_value('error-gemini-request', args={'error': error_detail})
             await thinking_message.edit_text(error_msg)
             return

        # Отправка основного ответа с обработкой ошибок парсинга
        try:
            await thinking_message.edit_text(response_text)
            logger.info(f"Ответ Gemini для user_id={user_id} сгенерирован (с форматированием).")
        except TelegramBadRequest as e:
            if "can't parse entities" in str(e):
                logger.warning(f"Ошибка парсинга Markdown для user_id={user_id}. Отправка без форматирования. Ошибка: {e}")
                try:
                    await thinking_message.edit_text(response_text, parse_mode=None)
                    logger.info(f"Ответ Gemini для user_id={user_id} сгенерирован (без форматирования).")
                except Exception as fallback_e:
                    logger.error(f"Не удалось отправить ответ Gemini даже без форматирования для user_id={user_id}: {fallback_e}", exc_info=True)
                    error_msg = localizer.format_value('error-display')
                    await thinking_message.edit_text(error_msg)
            else:
                logger.error(f"Неожиданная ошибка TelegramBadRequest для user_id={user_id}: {e}", exc_info=True)
                error_msg = localizer.format_value('error-general')
                await thinking_message.edit_text(error_msg)
        except Exception as e:
            logger.error(f"Общая ошибка при редактировании сообщения для user_id={user_id}: {e}", exc_info=True)
            error_msg = localizer.format_value('error-general')
            await thinking_message.edit_text(error_msg)
    else:
        error_msg = localizer.format_value('error-gemini-fetch')
        await thinking_message.edit_text(error_msg)
        logger.warning(f"Не удалось получить ответ Gemini для user_id={user_id}.")