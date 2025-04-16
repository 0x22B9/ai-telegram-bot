import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatAction
from fluent.runtime import FluentLocalization # Импорт
from typing import Dict, Any
import asyncio

from src.services import gemini
from src.db import get_history, save_history # Импортируем функции БД
from src.services.gemini import ( # Импортируем константы ошибок
    GEMINI_API_KEY_ERROR, GEMINI_BLOCKED_ERROR, GEMINI_REQUEST_ERROR
)
from src.config import DEFAULT_TEXT_MODEL

# Настройка логгирования
logger = logging.getLogger(__name__)

# Создаем роутер для текстовых сообщений
text_router = Router()

# Формат сообщения для истории Gemini
def create_gemini_message(role: str, text: str) -> Dict[str, Any]:
    """Создает сообщение в формате, ожидаемом Gemini API."""
    return {"role": role, "parts": [{"text": text}]}

# --- Вспомогательная функция для отправки "typing" ---
async def send_typing_periodically(bot: Bot, chat_id: int):
    """Отправляет 'typing' каждые 4 секунды, пока задача не будет отменена."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4) # Пауза меньше стандартного таймаута 'typing' (5 сек)
    except asyncio.CancelledError:
        # logger.debug(f"Typing task for chat {chat_id} cancelled.")
        pass # Ожидаемое завершение задачи
    except Exception as e:
        # Логируем другие возможные ошибки в фоновой задаче
        logger.error(f"Error in send_typing_periodically for chat {chat_id}: {e}", exc_info=True)
# ----------------------------------------------------

@text_router.message(F.text & ~F.text.startswith('/'))
async def handle_text_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    user_text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Текст от user_id={user_id} ({localizer.locales[0]}): {user_text[:50]}...")

    # Отправляем первоначальное сообщение "Думаю..."
    thinking_text = localizer.format_value('thinking')
    # Важно: Отправляем thinking_message ДО запуска typing, чтобы было что редактировать
    thinking_message = await message.answer(thinking_text)

    # --- Запускаем фоновую задачу для индикатора "typing" ---
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))
    # -----------------------------------------------------

    response_text = None
    error_code = None
    updated_history = None # Инициализируем на случай ошибки до присвоения
    save_needed = False

    try:
        # --- Основная логика ---
        # 1. Получить историю
        current_history = await get_history(user_id)
        logger.debug(f"Загружена история для user_id={user_id}, сообщений: {len(current_history)}")

        # 2. Получить модель
        user_data = await state.get_data()
        selected_model = user_data.get("selected_model", DEFAULT_TEXT_MODEL)
        logger.debug(f"Выбранная модель для user_id={user_id}: {selected_model}")

        # 3. Вызвать Gemini (может занять время)
        response_text, error_code = await gemini.generate_text_with_history(
            history=current_history,
            new_prompt=user_text,
            model_name=selected_model
        )

        # 4. Подготовить историю к сохранению (если успешно)
        if response_text and not error_code:
            user_msg_hist = create_gemini_message("user", user_text)
            model_msg_hist = create_gemini_message("model", response_text)
            updated_history = current_history + [user_msg_hist, model_msg_hist]
            save_needed = True
            logger.info(f"Gemini ({selected_model}) ответил user_id={user_id}.")
        elif error_code and error_code.startswith(GEMINI_BLOCKED_ERROR):
             # Сохраняем только сообщение юзера при блокировке
             user_msg_hist = create_gemini_message("user", user_text)
             updated_history = current_history + [user_msg_hist]
             save_needed = True
        # -----------------------

    finally:
        # --- Гарантированно останавливаем фоновую задачу "typing" ---
        if typing_task and not typing_task.done():
            typing_task.cancel()
            # Даем небольшой шанс задаче завершиться после отмены
            try:
                await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass # Игнорируем ожидаемые ошибки при отмене/таймауте
        # ------------------------------------------------------

    # --- Обработка результата и отправка ответа (после finally) ---
    final_response = ""
    if response_text and not error_code:
        final_response = response_text
    elif error_code:
        # Обработка кодов ошибок...
        if error_code == GEMINI_API_KEY_ERROR:
             final_response = localizer.format_value('error-gemini-api-key')
        elif error_code.startswith(GEMINI_BLOCKED_ERROR):
             reason = error_code.split(":", 1)[1] if ":" in error_code else "Неизвестно"
             final_response = localizer.format_value('error-blocked-content', args={'reason': reason})
        elif error_code.startswith(GEMINI_REQUEST_ERROR):
             error_detail = error_code.split(":", 1)[1] if ":" in error_code else "Неизвестная ошибка"
             final_response = localizer.format_value('error-gemini-request', args={'error': error_detail})
        else:
             final_response = localizer.format_value('error-general')
        logger.warning(f"Ошибка Gemini ({selected_model}) для user_id={user_id}: {error_code}")
    else:
        final_response = localizer.format_value('error-gemini-fetch')
        logger.error(f"Неожиданный результат от Gemini ({selected_model}) для user_id={user_id}: нет ни текста, ни ошибки.")

    # 5. Отправить ответ пользователю (редактируем исходное "Думаю...")
    try:
        # Используем thinking_message, которое отправили ранее
        await thinking_message.edit_text(final_response)
    except TelegramBadRequest as e:
        # ... (обработка ошибок парсинга, без изменений) ...
        if "can't parse entities" in str(e):
            logger.warning(f"Ошибка парсинга Markdown ({selected_model}) для user_id={user_id}. Отправка plain text.")
            try:
                await thinking_message.edit_text(final_response, parse_mode=None)
            except Exception as fallback_e:
                logger.error(f"Не удалось отправить ответ ({selected_model}) plain text для user_id={user_id}: {fallback_e}", exc_info=True)
                error_msg = localizer.format_value('error-display')
                await thinking_message.edit_text(error_msg)
                save_needed = False # Не сохраняем, если не смогли отправить
        else:
            logger.error(f"Неожиданная ошибка TelegramBadRequest ({selected_model}) для user_id={user_id}: {e}", exc_info=True)
            error_msg = localizer.format_value('error-general')
            await thinking_message.edit_text(error_msg)
            save_needed = False
    except Exception as e:
        logger.error(f"Общая ошибка при редактировании сообщения ({selected_model}) для user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-general')
        await thinking_message.edit_text(error_msg)
        save_needed = False

    # 6. Сохранить обновленную историю в БД (если нужно)
    if save_needed and updated_history is not None: # Добавил проверку на None
        await save_history(user_id, updated_history)
    elif save_needed and updated_history is None:
         logger.error(f"Попытка сохранить историю для user_id={user_id}, но updated_history is None!")