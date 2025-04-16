import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatAction
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization # Импорт
from typing import Dict, Any
import asyncio

from src.services import gemini
from src.db import get_history, save_history # Импортируем функции БД
from src.services.gemini import ( # Импортируем константы ошибок
    GEMINI_API_KEY_ERROR, GEMINI_BLOCKED_ERROR, GEMINI_REQUEST_ERROR
)
from src.config import DEFAULT_TEXT_MODEL
from src.keyboards import get_main_keyboard

# Настройка логгирования
logger = logging.getLogger(__name__)

# Создаем роутер для текстовых сообщений
text_router = Router()

LAST_FAILED_PROMPT_KEY = "last_failed_prompt"
# Callback data для кнопки повтора
RETRY_CALLBACK_DATA = "retry_last_prompt"
# Формат сообщения для истории Gemini

def create_gemini_message(role: str, text: str) -> Dict[str, Any]:
    """Создает сообщение в формате, ожидаемом Gemini API."""
    return {"role": role, "parts": [{"text": text}]}

async def send_typing_periodically(bot: Bot, chat_id: int):
    """Отправляет 'typing' каждые 4 секунды, пока задача не будет отменена."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4) # Пауза меньше стандартного таймаута 'typing' (5 сек)
    except asyncio.CancelledError:
        logger.debug(f"Typing task for chat {chat_id} cancelled.")
        pass # Ожидаемое завершение задачи
    except Exception as e:
        logger.error(f"Error in send_typing_periodically for chat {chat_id}: {e}", exc_info=True)
# ----------------------------------------------------

@text_router.message(F.text & ~F.text.startswith('/'))
async def handle_text_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    user_text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Текст от user_id={user_id} ({localizer.locales[0]}): {user_text[:50]}...")

    # Сразу очистим предыдущий неудачный запрос, если он был
    await state.update_data({LAST_FAILED_PROMPT_KEY: None})

    thinking_text = localizer.format_value('thinking')
    thinking_message = await message.answer(thinking_text)
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))

    response_text = None
    error_code = None
    updated_history = None
    save_needed = False
    selected_model = DEFAULT_TEXT_MODEL # Инициализация на случай ошибки до получения из state

    try:
        current_history = await get_history(user_id)
        user_data = await state.get_data()
        selected_model = user_data.get("selected_model", DEFAULT_TEXT_MODEL)

        response_text, error_code = await gemini.generate_text_with_history(
            history=current_history,
            new_prompt=user_text,
            model_name=selected_model
        )

        if response_text and not error_code:
            user_msg_hist = create_gemini_message("user", user_text)
            model_msg_hist = create_gemini_message("model", response_text)
            updated_history = current_history + [user_msg_hist, model_msg_hist]
            save_needed = True
            logger.info(f"Gemini ({selected_model}) ответил user_id={user_id}.")
        elif error_code and error_code.startswith(GEMINI_BLOCKED_ERROR):
             user_msg_hist = create_gemini_message("user", user_text)
             updated_history = current_history + [user_msg_hist]
             save_needed = True
        # Не сохраняем историю при ошибках API ключа или запроса Gemini

    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    # --- Обработка результата и ОТПРАВКА ОТВЕТА / КНОПКИ ПОВТОРА ---
    final_response = ""
    reply_markup = None # По умолчанию без inline кнопок

    # --- Определяем, нужна ли кнопка повтора ---
    show_retry_button = False
    if error_code and error_code.startswith(GEMINI_REQUEST_ERROR):
        show_retry_button = True
        error_detail = error_code.split(":", 1)[1] if ":" in error_code else "Unknown Error"
        final_response = localizer.format_value('error-gemini-request', args={'error': error_detail})
        logger.warning(f"Ошибка запроса Gemini ({selected_model}) для user_id={user_id}: {error_code}")
    elif not response_text and not error_code: # Случай, когда Gemini вернул пустой ответ без ошибки
        show_retry_button = True
        final_response = localizer.format_value('error-gemini-fetch')
        logger.error(f"Неожиданный результат от Gemini ({selected_model}) для user_id={user_id}: нет ни текста, ни ошибки.")

    # --- Сохраняем промпт и создаем кнопку, если нужно ---
    if show_retry_button:
        await state.update_data({LAST_FAILED_PROMPT_KEY: user_text}) # Сохраняем текст для повтора
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup() # Устанавливаем клавиатуру
    elif error_code and error_code == GEMINI_API_KEY_ERROR:
        final_response = localizer.format_value('error-gemini-api-key')
        logger.error(f"Ошибка ключа API Gemini для user_id={user_id}")
    elif error_code and error_code.startswith(GEMINI_BLOCKED_ERROR):
        reason = error_code.split(":", 1)[1] if ":" in error_code else "Неизвестно"
        final_response = localizer.format_value('error-blocked-content', args={'reason': reason})
        logger.warning(f"Ответ Gemini заблокирован ({selected_model}) для user_id={user_id}. Причина: {reason}")
    elif response_text and not error_code:
        final_response = response_text # Успешный ответ

    # Отправляем/Редактируем сообщение
    try:
        await thinking_message.edit_text(final_response, reply_markup=reply_markup) # Передаем клавиатуру (или None)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
             # Игнорируем ошибку, если сообщение не изменилось (например, ошибка та же)
             logger.debug(f"Сообщение {thinking_message.message_id} не было изменено.")
        elif "can't parse entities" in str(e):
            logger.warning(f"Ошибка парсинга Markdown ({selected_model}) для user_id={user_id}. Отправка plain text.")
            try:
                # Повторно отправляем с кнопкой (если она была) и без парсинга
                await thinking_message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
            except Exception as fallback_e:
                logger.error(f"Не удалось отправить ответ ({selected_model}) plain text для user_id={user_id}: {fallback_e}", exc_info=True)
                error_msg = localizer.format_value('error-display')
                await thinking_message.edit_text(error_msg) # Убираем кнопку при фатальной ошибке отправки
                save_needed = False
        else:
            logger.error(f"Неожиданная ошибка TelegramBadRequest ({selected_model}) для user_id={user_id}: {e}", exc_info=True)
            error_msg = localizer.format_value('error-general')
            await thinking_message.edit_text(error_msg) # Убираем кнопку при фатальной ошибке отправки
            save_needed = False
    except Exception as e:
        logger.error(f"Общая ошибка при редактировании сообщения ({selected_model}) для user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-general')
        await thinking_message.edit_text(error_msg) # Убираем кнопку при фатальной ошибке отправки
        save_needed = False

    # Сохраняем историю (только если был успешный ответ или блокировка)
    if save_needed and updated_history is not None:
        await save_history(user_id, updated_history)
    elif save_needed and updated_history is None:
         logger.error(f"Попытка сохранить историю для user_id={user_id}, но updated_history is None!")


# --- НОВЫЙ ОБРАБОТЧИК для кнопки "Повторить запрос?" ---
@text_router.callback_query(F.data == RETRY_CALLBACK_DATA)
async def handle_retry_request(callback: types.CallbackQuery, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    """Обрабатывает нажатие на кнопку 'Повторить запрос?'."""
    await callback.answer() # Отвечаем на колбэк
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id if callback.message else user_id # Получаем chat_id

    user_data = await state.get_data()
    original_prompt = user_data.get(LAST_FAILED_PROMPT_KEY)

    if not original_prompt:
        logger.warning(f"Не найден текст для повтора (user_id={user_id}). Возможно, состояние очищено.")
        # Убираем кнопку и сообщаем об ошибке
        try:
            if callback.message:
                await callback.message.edit_text(localizer.format_value('error-retry-not-found'), reply_markup=None)
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения 'retry not found' для user_id={user_id}: {e}")
        return

    logger.info(f"Повтор запроса для user_id={user_id}: {original_prompt[:50]}...")

    retry_status_text = localizer.format_value('thinking-retry') # Нужна новая строка локализации
    try:
        if callback.message:
            await callback.message.edit_text(retry_status_text, reply_markup=None)
    except Exception as e:
        logger.warning(f"Не удалось обновить статус перед повтором для user_id={user_id}: {e}")
        # Все равно продолжаем

    # --- Повторяем логику запроса (аналогично handle_text_message) ---
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))
    response_text = None
    error_code = None
    updated_history = None
    save_needed = False
    selected_model = DEFAULT_TEXT_MODEL

    try:
        current_history = await get_history(user_id)
        # Модель уже должна быть в state, если пользователь ее выбирал
        selected_model = user_data.get("selected_model", DEFAULT_TEXT_MODEL)

        response_text, error_code = await gemini.generate_text_with_history(
            history=current_history,
            new_prompt=original_prompt, # Используем сохраненный промпт
            model_name=selected_model
        )

        # Обработка истории при успехе или блокировке (как в основном хэндлере)
        if response_text and not error_code:
            user_msg_hist = create_gemini_message("user", original_prompt)
            model_msg_hist = create_gemini_message("model", response_text)
            updated_history = current_history + [user_msg_hist, model_msg_hist]
            save_needed = True
            await state.update_data({LAST_FAILED_PROMPT_KEY: None}) # Очищаем промпт после успеха
            logger.info(f"Повторный запрос Gemini ({selected_model}) успешен для user_id={user_id}.")
        elif error_code and error_code.startswith(GEMINI_BLOCKED_ERROR):
             user_msg_hist = create_gemini_message("user", original_prompt)
             updated_history = current_history + [user_msg_hist]
             save_needed = True
             await state.update_data({LAST_FAILED_PROMPT_KEY: None}) # Очищаем промпт и при блокировке
             logger.warning(f"Повторный запрос Gemini ({selected_model}) заблокирован для user_id={user_id}.")
        # При других ошибках промпт остается в state для возможного следующего повтора

    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    # --- Обработка результата повторного запроса ---
    final_response = ""
    reply_markup = None # По умолчанию без кнопки

    # Определяем, нужна ли кнопка повтора СНОВА
    show_retry_button_again = False
    if error_code and error_code.startswith(GEMINI_REQUEST_ERROR):
        show_retry_button_again = True
        error_detail = error_code.split(":", 1)[1] if ":" in error_code else "Unknown Error"
        final_response = localizer.format_value('error-gemini-request', args={'error': error_detail})
        logger.warning(f"Повторный запрос Gemini ({selected_model}) снова неудачен для user_id={user_id}: {error_code}")
    elif not response_text and not error_code:
        show_retry_button_again = True
        final_response = localizer.format_value('error-gemini-fetch')
        logger.error(f"Повторный запрос Gemini ({selected_model}) снова вернул пустой ответ для user_id={user_id}.")

    if show_retry_button_again:
        # Промпт уже должен быть в state, просто создаем кнопку
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
    elif error_code and error_code == GEMINI_API_KEY_ERROR:
        final_response = localizer.format_value('error-gemini-api-key')
    elif error_code and error_code.startswith(GEMINI_BLOCKED_ERROR):
        reason = error_code.split(":", 1)[1] if ":" in error_code else "Неизвестно"
        final_response = localizer.format_value('error-blocked-content', args={'reason': reason})
    elif response_text and not error_code:
        final_response = response_text

    # Редактируем сообщение, которое показывало "Повторяю запрос..."
    try:
        if callback.message:
            await callback.message.edit_text(final_response, reply_markup=reply_markup)
        else: # Если исходного сообщения нет (очень редкий случай)
             # Отправляем новое сообщение с основной клавиатурой
             main_kbd = get_main_keyboard(localizer)
             await bot.send_message(chat_id, final_response, reply_markup=main_kbd)

    except TelegramBadRequest as e:
        # ... (обработка ошибок парсинга и т.д. как в основном хэндлере) ...
        if "message is not modified" in str(e):
             logger.debug(f"Сообщение {callback.message.message_id if callback.message else 'unknown'} не было изменено после повтора.")
        elif "can't parse entities" in str(e):
            logger.warning(f"Ошибка парсинга Markdown при повторе ({selected_model}) для user_id={user_id}.")
            try:
                if callback.message:
                    await callback.message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
            except Exception as fallback_e:
                logger.error(f"Не удалось отправить ответ при повторе ({selected_model}) plain text для user_id={user_id}: {fallback_e}", exc_info=True)
                # Фоллбек: отправить новое сообщение
                error_msg = localizer.format_value('error-display')
                main_kbd = get_main_keyboard(localizer)
                await bot.send_message(chat_id, error_msg, reply_markup=main_kbd)
                save_needed = False # Не сохраняем при ошибке отправки
        else:
             logger.error(f"Неожиданная ошибка TelegramBadRequest при повторе ({selected_model}) для user_id={user_id}: {e}", exc_info=True)
             error_msg = localizer.format_value('error-general')
             main_kbd = get_main_keyboard(localizer)
             await bot.send_message(chat_id, error_msg, reply_markup=main_kbd)
             save_needed = False
    except Exception as e:
        logger.error(f"Общая ошибка при редактировании сообщения при повторе ({selected_model}) для user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-general')
        main_kbd = get_main_keyboard(localizer)
        await bot.send_message(chat_id, error_msg, reply_markup=main_kbd)
        save_needed = False

    # Сохраняем историю (если нужно)
    if save_needed and updated_history is not None:
        await save_history(user_id, updated_history)
    elif save_needed and updated_history is None:
        logger.error(f"Попытка сохранить историю при повторе для user_id={user_id}, но updated_history is None!")