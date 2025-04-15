import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from fluent.runtime import FluentLocalization # Импорт
from typing import Dict, Any

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

@text_router.message(F.text & ~F.text.startswith('/'))
async def handle_text_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    user_text = message.text
    user_id = message.from_user.id
    logger.info(f"Текст от user_id={user_id} ({localizer.locales[0]}): {user_text[:50]}...")

    thinking_text = localizer.format_value('thinking')
    thinking_message = await message.answer(thinking_text)

    # 1. Получить текущую историю из БД
    current_history = await get_history(user_id)
    logger.debug(f"Загружена история для user_id={user_id}, сообщений: {len(current_history)}")

    user_data = await state.get_data()
    selected_model = user_data.get("selected_model", DEFAULT_TEXT_MODEL) # Используем дефолт, если не выбрана
    logger.debug(f"Выбранная модель для user_id={user_id}: {selected_model}")

    # 2. Вызвать Gemini с историей и новым сообщением
    response_text, error_code = await gemini.generate_text_with_history(
        history=current_history,
        new_prompt=user_text,
        model_name=selected_model # <<< Передаем модель
    )

    # 3. Обработать ответ или ошибку
    final_response = ""
    save_needed = False # Флаг, нужно ли сохранять историю
    updated_history = current_history

    if response_text and not error_code:
        final_response = response_text
        user_message_for_history = create_gemini_message("user", user_text)
        model_message_for_history = create_gemini_message("model", response_text)
        updated_history = current_history + [user_message_for_history, model_message_for_history]
        save_needed = True
        logger.info(f"Gemini ({selected_model}) ответил user_id={user_id}. Новая длина истории: {len(updated_history)}")

    elif error_code:
        # Обработка кодов ошибок Gemini
        if error_code == GEMINI_API_KEY_ERROR:
            final_response = localizer.format_value('error-gemini-api-key')
        elif error_code.startswith(GEMINI_BLOCKED_ERROR):
            reason = error_code.split(":", 1)[1] if ":" in error_code else "Неизвестно"
            final_response = localizer.format_value('error-blocked-content', args={'reason': reason})
            user_message_for_history = create_gemini_message("user", user_text)
            updated_history = current_history + [user_message_for_history] # Сохраняем только сообщение юзера
            save_needed = True
        elif error_code.startswith(GEMINI_REQUEST_ERROR):
            error_detail = error_code.split(":", 1)[1] if ":" in error_code else "Неизвестная ошибка"
            final_response = localizer.format_value('error-gemini-request', args={'error': error_detail})
            save_needed = False # Не сохраняем при ошибке запроса
        else:
            final_response = localizer.format_value('error-general')
        logger.warning(f"Ошибка Gemini ({selected_model}) для user_id={user_id}: {error_code}")
    else:
        final_response = localizer.format_value('error-gemini-fetch')
        logger.error(f"Неожиданный результат от Gemini ({selected_model}) для user_id={user_id}: нет ни текста, ни ошибки.")

    # 5. Отправить ответ пользователю (с обработкой ошибок парсинга)
    try:
        await thinking_message.edit_text(final_response)
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e):
            logger.warning(f"Ошибка парсинга HTML ({selected_model}) для user_id={user_id}. Отправка plain text.")
            try:
                await thinking_message.edit_text(final_response, parse_mode=None)
            except Exception as fallback_e:
                logger.error(f"Не удалось отправить ответ ({selected_model}) plain text для user_id={user_id}: {fallback_e}", exc_info=True)
                error_msg = localizer.format_value('error-display')
                await thinking_message.edit_text(error_msg)
                save_needed = False
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
    if save_needed:
        await save_history(user_id, updated_history)
        logger.info(f"История для user_id={user_id} сохранена.")