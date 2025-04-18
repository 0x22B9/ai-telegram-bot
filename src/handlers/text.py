import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization # Импорт
from typing import List, Dict, Any, Tuple, Optional
import asyncio

from src.utils.text_processing import strip_markdown
from src.services import gemini
from src.db import get_history, get_user_settings, save_history 
from src.services.gemini import ( # Импортируем константы ошибок
    GEMINI_API_KEY_ERROR, GEMINI_BLOCKED_ERROR, GEMINI_REQUEST_ERROR, GEMINI_QUOTA_ERROR
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

async def _process_text_input(
    user_text: str,
    user_id: int,
    state: FSMContext,
    localizer: FluentLocalization
) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Обрабатывает текстовый ввод пользователя: запрашивает Gemini, обрабатывает ответ.
    Возвращает: (текст_ответа_пользователю, обновленная_история_для_сохранения | None, текст_исходного_запроса_для_повтора | None)
    """
    updated_history = None
    failed_prompt_for_retry = None

    try:
        # 1. Получаем историю и настройки
        current_history = await get_history(user_id)
        user_temp, user_max_tokens = await get_user_settings(user_id)
        user_data = await state.get_data()
        selected_model = user_data.get("selected_model", DEFAULT_TEXT_MODEL)
        logger.debug(f"Processing text with: model={selected_model}, temp={user_temp}, tokens={user_max_tokens}")

        # 2. Вызываем Gemini
        response_text, error_code = await gemini.generate_text_with_history(
            history=current_history,
            new_prompt=user_text,
            model_name=selected_model,
            temperature=user_temp,
            max_output_tokens=user_max_tokens
        )

        # 3. Обрабатываем результат
        if response_text and not error_code:
            final_response = strip_markdown(response_text)
            user_msg_hist = create_gemini_message("user", user_text)
            model_msg_hist = create_gemini_message("model", response_text)
            updated_history = current_history + [user_msg_hist, model_msg_hist]
            logger.info(f"Gemini ({selected_model}) ответил user_id={user_id}.")
        elif error_code:
            logger.warning(f"Ошибка Gemini ({selected_model}) для user_id={user_id}: {error_code}")
            if error_code == GEMINI_QUOTA_ERROR:
                final_response = localizer.format_value('error-quota-exceeded')
            elif error_code.startswith(GEMINI_REQUEST_ERROR):
                error_detail = error_code.split(":", 1)[1] if ":" in error_code else "Unknown Error"
                final_response = localizer.format_value('error-gemini-request', args={'error': error_detail})
                failed_prompt_for_retry = user_text # Сохраняем промпт для кнопки "Повторить"
            elif error_code == GEMINI_API_KEY_ERROR:
                final_response = localizer.format_value('error-gemini-api-key')
            elif error_code.startswith(GEMINI_BLOCKED_ERROR):
                reason = error_code.split(":", 1)[1] if ":" in error_code else "Неизвестно"
                final_response = localizer.format_value('error-blocked-content', args={'reason': reason})
                # Сохраняем историю только с сообщением пользователя при блокировке
                user_msg_hist = create_gemini_message("user", user_text)
                updated_history = current_history + [user_msg_hist]
            else: # Неизвестный код ошибки от Gemini
                final_response = localizer.format_value('error-general')
        else: # Пустой ответ без ошибки
            logger.error(f"Неожиданный результат от Gemini ({selected_model}) для user_id={user_id}: нет ни текста, ни ошибки.")
            final_response = localizer.format_value('error-gemini-fetch')
            failed_prompt_for_retry = user_text # Сохраняем промпт для кнопки "Повторить"

        return final_response, updated_history, failed_prompt_for_retry

    except Exception as e:
        # Ловим непредвиденные ошибки в самом процессе обработки
        logger.error(f"Непредвиденная ошибка в _process_text_input для user_id={user_id}: {e}", exc_info=True)
        final_response = localizer.format_value("error-general")
        return final_response, None, None # Не сохраняем историю и не предлагаем повторить

@text_router.message(
    F.text & ~F.text.startswith('/'),
    StateFilter(None)
)
async def handle_text_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    user_text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(f"Текст от user_id={user_id} ({localizer.locales[0]}): {user_text[:50]}...")

    await state.update_data({LAST_FAILED_PROMPT_KEY: None})
    thinking_text = localizer.format_value('thinking')
    thinking_message = await message.answer(thinking_text)
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))

    final_response = localizer.format_value("error-general") # Значение по умолчанию
    updated_history = None
    failed_prompt = None

    try:
        # --- Вызываем ядро обработки ---
        final_response, updated_history, failed_prompt = await _process_text_input(
            user_text=user_text,
            user_id=user_id,
            state=state,
            localizer=localizer
        )
        # -----------------------------
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    # --- Пост-обработка: кнопка "Повторить" и отправка ---
    reply_markup = None
    save_needed = updated_history is not None # Флаг для сохранения истории

    if failed_prompt: # Если _process_text_input вернул промпт для повтора
        await state.update_data({LAST_FAILED_PROMPT_KEY: failed_prompt})
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False # Не сохраняем историю при ошибке, требующей повтора

    # Отправляем/Редактируем сообщение
    try:
        await thinking_message.edit_text(final_response, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
             logger.debug(f"Сообщение {thinking_message.message_id} не было изменено.")
        elif "can't parse entities" in str(e):
            logger.warning(f"Ошибка парсинга Markdown для user_id={user_id}. Отправка plain text.")
            try:
                await thinking_message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
            except Exception as fallback_e:
                logger.error(f"Не удалось отправить ответ plain text для user_id={user_id}: {fallback_e}", exc_info=True)
                error_msg = localizer.format_value('error-display')
                await thinking_message.edit_text(error_msg)
                save_needed = False
        else:
            logger.error(f"Неожиданная ошибка TelegramBadRequest для user_id={user_id}: {e}", exc_info=True)
            error_msg = localizer.format_value('error-general')
            await thinking_message.edit_text(error_msg)
            save_needed = False
    except Exception as e:
        logger.error(f"Общая ошибка при редактировании сообщения для user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-general')
        await thinking_message.edit_text(error_msg)
        save_needed = False

    # Сохраняем историю (только если был успешный ответ или блокировка)
    if save_needed and updated_history is not None:
        await save_history(user_id, updated_history)
    elif save_needed and updated_history is None:
         logger.error(f"Попытка сохранить историю для user_id={user_id}, но updated_history is None!")


# --- НОВЫЙ ОБРАБОТЧИК для кнопки "Повторить запрос?" ---
@text_router.callback_query(F.data == RETRY_CALLBACK_DATA)
async def handle_retry_request(callback: types.CallbackQuery, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    await callback.answer()
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id if callback.message else user_id
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
    retry_status_text = localizer.format_value('thinking-retry')
    status_message = None
    if callback.message:
        try:
            await callback.message.edit_text(retry_status_text, reply_markup=None)
            status_message = callback.message # Сохраняем сообщение для дальнейшего редактирования
        except Exception as e: logger.warning(f"Не удалось обновить статус перед повтором для user_id={user_id}: {e}")
    else:
        # Если исходного сообщения нет, нужно отправить новое статусное
        status_message = await bot.send_message(chat_id, retry_status_text)

    # --- Повторяем логику запроса (аналогично handle_text_message) ---
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))
    final_response = localizer.format_value("error-general")
    updated_history = None
    failed_prompt = None

    try:
        # --- Вызываем ядро обработки с ОРИГИНАЛЬНЫМ промптом ---
        final_response, updated_history, failed_prompt = await _process_text_input(
            user_text=original_prompt, # <<< Используем original_prompt
            user_id=user_id,
            state=state,
            localizer=localizer
        )
        # ---------------------------------------------------
        # Очищаем промпт из state ТОЛЬКО при успехе или блокировке
        if not failed_prompt and updated_history is not None:
             await state.update_data({LAST_FAILED_PROMPT_KEY: None})

    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    # --- Пост-обработка для повтора ---
    reply_markup = None
    save_needed = updated_history is not None

    if failed_prompt: # Если повторный запрос снова не удался
        # Промпт уже должен быть в state, т.к. мы его не очищали при ошибке
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False # Не сохраняем историю при ошибке

    # Редактируем сообщение со статусом "Повторяю..."
    if status_message:
        try:
            await status_message.edit_text(final_response, reply_markup=reply_markup)
        except TelegramBadRequest as e:
        # ... (обработка ошибок парсинга и т.д. как в основном хэндлере) ...
            if "message is not modified" in str(e): pass # Игнор
            elif "can't parse entities" in str(e):
                logger.warning(f"Ошибка парсинга Markdown при повторе для user_id={user_id}.")
                try: await status_message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
                except Exception as fallback_e: logger.error(f"Не удалось отправить ответ при повторе plain text для user_id={user_id}: {fallback_e}", exc_info=True); save_needed = False
            else:
                logger.error(f"Неожиданная ошибка TelegramBadRequest при повторе для user_id={user_id}: {e}", exc_info=True); save_needed = False
        except Exception as e:
            logger.error(f"Общая ошибка при редактировании сообщения при повторе для user_id={user_id}: {e}", exc_info=True); save_needed = False
    else: # Если не было исходного сообщения для редактирования
        main_kbd = get_main_keyboard(localizer)
        await bot.send_message(chat_id, final_response, reply_markup=main_kbd) # Отправляем новое

    # Сохраняем историю (если нужно)
    if save_needed and updated_history is not None:
        await save_history(user_id, updated_history)
    elif save_needed and updated_history is None:
        logger.error(f"Попытка сохранить историю при повторе для user_id={user_id}, но updated_history is None!")