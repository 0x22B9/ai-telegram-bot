import logging
import io
import asyncio
from aiogram import Router, F, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction
from fluent.runtime import FluentLocalization
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional

from src.services import document_parser as doc_parser # Импортируем парсер
# Импортируем функции и константы из text.py для обработки текста
from src.handlers.text import (
    _process_text_input, send_typing_periodically,
    LAST_FAILED_PROMPT_KEY, RETRY_CALLBACK_DATA
)
from src.db import save_history # Для сохранения истории

logger = logging.getLogger(__name__)
document_router = Router()

# Определяем максимальный размер файла для обработки (в байтах)
# Например, 20 МБ (Telegram позволяет до 50 МБ для ботов, но обработка больших файлов ресурсоемка)
MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024

@document_router.message(F.document, StateFilter(None)) # Ловим документы, когда нет состояния FSM
async def handle_document_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    user_id = message.from_user.id
    chat_id = message.chat.id
    document = message.document

    # 0. Проверяем MIME-тип на поддерживаемый ПЕРЕД скачиванием
    mime_type = document.mime_type
    if mime_type not in doc_parser.SUPPORTED_MIME_TYPES:
        logger.info(f"Получен неподдерживаемый документ от user_id={user_id}, mime_type={mime_type}, filename={document.file_name}")
        error_text = localizer.format_value("error-doc-unsupported-type", args={"mime_type": mime_type})
        await message.reply(error_text)
        return

    # 1. Проверяем размер файла ПЕРЕД скачиванием
    if document.file_size > MAX_DOCUMENT_SIZE_BYTES:
        logger.warning(f"Документ от user_id={user_id} слишком большой: {document.file_size / (1024*1024):.2f} МБ")
        error_text = localizer.format_value("error-doc-too-large", args={"limit_mb": MAX_DOCUMENT_SIZE_BYTES / (1024*1024)})
        await message.reply(error_text)
        return

    logger.info(f"Получен документ от user_id={user_id}: mime_type={mime_type}, filename={document.file_name}, size={document.file_size}")

    # 2. Статус и индикатор
    processing_doc_text = localizer.format_value("processing-document", args={"filename": document.file_name})
    status_message = await message.answer(processing_doc_text)
    # Используем typing, так как дальше будет обработка текста
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))

    extracted_text: Optional[str] = None
    parsing_error_code: Optional[str] = None
    final_response: str = localizer.format_value("error-general") # Дефолт
    updated_history = None
    failed_prompt_for_retry = None
    save_needed = False

    try:
        # 3. Скачиваем документ
        logger.debug(f"Начинаю скачивание документа {document.file_id}...")
        doc_bytes_io = io.BytesIO()
        await bot.download(file=document, destination=doc_bytes_io)
        doc_bytes = doc_bytes_io.getvalue()
        doc_bytes_io.close() # Закрываем BytesIO после чтения
        logger.debug(f"Документ {document.file_id} скачан ({len(doc_bytes)} байт).")

        # 4. Извлекаем текст
        extracted_text, parsing_error_code = await doc_parser.extract_text_from_document(
            file_bytes=doc_bytes,
            mime_type=mime_type
        )

        if extracted_text and parsing_error_code == doc_parser.PARSING_SUCCESS:
            logger.info(f"Текст из документа {document.file_name} извлечен ({len(extracted_text)} символов).")
            # --- Если извлечение успешно, ОБРАБАТЫВАЕМ ТЕКСТ ---
            processing_text_status = localizer.format_value("processing-extracted-text", args={"filename": document.file_name})
            await status_message.edit_text(processing_text_status)

            # Формируем промпт для Gemini (можно настроить)
            # Можно добавить информацию о файле в начало
            user_input_for_gemini = f"Проанализируй следующий текст из документа '{document.file_name}':\n\n{extracted_text}"
            # Или просто передать текст: user_input_for_gemini = extracted_text

            final_response, updated_history, failed_prompt_for_retry = await _process_text_input(
                user_text=user_input_for_gemini, # Используем извлеченный текст + возможно доп. инфо
                user_id=user_id,
                state=state,
                localizer=localizer
            )
            # Если обработка текста прошла успешно (нет failed_prompt_for_retry), то ставим флаг на сохранение
            save_needed = updated_history is not None and not failed_prompt_for_retry

        else:
            # --- Обработка ошибок парсинга ---
            logger.warning(f"Ошибка извлечения текста из {document.file_name} для user_id={user_id}: {parsing_error_code}")
            # Генерируем ключ ошибки из кода
            error_key = f"error-doc-parsing-{parsing_error_code.split('_')[-1].lower()}"
            # Особый случай для недостающей библиотеки
            if parsing_error_code == doc_parser.PARSING_LIB_MISSING:
                 error_lib = "pypdf" if mime_type == "application/pdf" else "python-docx"
                 final_response = localizer.format_value("error-doc-parsing-lib_missing", args={"library": error_lib})
            else:
                 final_response = localizer.format_value(error_key, fallback=localizer.format_value("error-doc-parsing-unknown")) # Фоллбэк на общую ошибку
            # Кнопку повтора для парсинга не делаем

    except Exception as e:
        # Ловим ошибки скачивания или другие неожиданные ошибки
        logger.error(f"Ошибка при обработке документа от user_id={user_id}: {e}", exc_info=True)
        final_response = localizer.format_value("error-doc-processing-general")
    finally:
        # Гарантированно останавливаем индикатор
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    # --- Пост-обработка: кнопка "Повторить" для ОШИБКИ ОБРАБОТКИ ТЕКСТА ---
    reply_markup = None
    if failed_prompt_for_retry: # Если была ошибка именно при обработке текста _после_ парсинга
        await state.update_data({LAST_FAILED_PROMPT_KEY: failed_prompt_for_retry})
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False # Не сохраняем историю при ошибке текста

    # Редактируем статусное сообщение
    try:
        # Ограничиваем длину ответа, т.к. он может быть очень большим после анализа документа
        MAX_RESPONSE_LEN = 4000 # Чуть меньше лимита Telegram в 4096
        if len(final_response) > MAX_RESPONSE_LEN:
            cutoff_msg = localizer.format_value("response-truncated")
            final_response = final_response[:MAX_RESPONSE_LEN] + f"\n\n{cutoff_msg}"

        await status_message.edit_text(final_response, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        # ... (обработка ошибок парсинга и message is not modified - копипаста из text.py/audio.py) ...
        if "message is not modified" in str(e): pass
        elif "can't parse entities" in str(e):
            logger.warning(f"Ошибка парсинга Markdown после обработки документа для user_id={user_id}.")
            try: await status_message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
            except Exception as fallback_e: logger.error(f"Не удалось отправить ответ после док-та plain text для user_id={user_id}: {fallback_e}", exc_info=True); save_needed = False
        else:
            logger.error(f"Неожиданная ошибка TelegramBadRequest после док-та для user_id={user_id}: {e}", exc_info=True); save_needed = False
    except Exception as e:
        logger.error(f"Общая ошибка при ред-ии сообщения после док-та для user_id={user_id}: {e}", exc_info=True); save_needed = False

    # Сохраняем историю, если нужно (т.е. если обработка текста была успешной)
    if save_needed and updated_history:
        await save_history(user_id, updated_history)