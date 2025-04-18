import logging
import io
import asyncio
from aiogram import Router, F, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from fluent.runtime import FluentLocalization
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional

from src.services import document_parser as doc_parser
from src.handlers.text import (
    _process_text_input, send_typing_periodically,
    LAST_FAILED_PROMPT_KEY, RETRY_CALLBACK_DATA
)
from src.db import save_history

logger = logging.getLogger(__name__)
document_router = Router()

MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024

@document_router.message(F.document, StateFilter(None))
async def handle_document_message(message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization):
    user_id = message.from_user.id
    chat_id = message.chat.id
    document = message.document

    mime_type = document.mime_type
    if mime_type not in doc_parser.SUPPORTED_MIME_TYPES:
        logger.info(f"Got unsupported document from user_id={user_id}, mime_type={mime_type}, filename={document.file_name}")
        error_text = localizer.format_value("error-doc-unsupported-type", args={"mime_type": mime_type})
        await message.reply(error_text)
        return

    if document.file_size > MAX_DOCUMENT_SIZE_BYTES:
        logger.warning(f"Document from user_id={user_id} is too large: {document.file_size / (1024*1024):.2f} MB")
        error_text = localizer.format_value("error-doc-too-large", args={"limit_mb": MAX_DOCUMENT_SIZE_BYTES / (1024*1024)})
        await message.reply(error_text)
        return

    logger.info(f"Got document from user_id={user_id}: mime_type={mime_type}, filename={document.file_name}, size={document.file_size}")

    processing_doc_text = localizer.format_value("processing-document", args={"filename": document.file_name})
    status_message = await message.answer(processing_doc_text)
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))

    extracted_text: Optional[str] = None
    parsing_error_code: Optional[str] = None
    final_response: str = localizer.format_value("error-general")
    updated_history = None
    failed_prompt_for_retry = None
    save_needed = False

    try:
        logger.debug(f"Starting download of document {document.file_id}...")
        doc_bytes_io = io.BytesIO()
        await bot.download(file=document, destination=doc_bytes_io)
        doc_bytes = doc_bytes_io.getvalue()
        doc_bytes_io.close()
        logger.debug(f"Document {document.file_id} downloaded ({len(doc_bytes)} bytes).")

        extracted_text, parsing_error_code = await doc_parser.extract_text_from_document(
            file_bytes=doc_bytes,
            mime_type=mime_type
        )

        if extracted_text and parsing_error_code == doc_parser.PARSING_SUCCESS:
            logger.info(f"Text from document {document.file_name} extracted ({len(extracted_text)} symbols).")
            processing_text_status = localizer.format_value("processing-extracted-text", args={"filename": document.file_name})
            await status_message.edit_text(processing_text_status)

            user_input_for_gemini = f"Проанализируй текст из этого документа '{document.file_name}':\n\n{extracted_text}"

            final_response, updated_history, failed_prompt_for_retry = await _process_text_input(
                user_text=user_input_for_gemini,
                user_id=user_id,
                state=state,
                localizer=localizer
            )
            save_needed = updated_history is not None and not failed_prompt_for_retry

        else:
            logger.warning(f"Error text extraction from document {document.file_name} for user_id={user_id}: {parsing_error_code}")
            error_key = f"error-doc-parsing-{parsing_error_code.split('_')[-1].lower()}"
            if parsing_error_code == doc_parser.PARSING_LIB_MISSING:
                 error_lib = "pypdf" if mime_type == "application/pdf" else "python-docx"
                 final_response = localizer.format_value("error-doc-parsing-lib_missing", args={"library": error_lib})
            else:
                 final_response = localizer.format_value(error_key, fallback=localizer.format_value("error-doc-parsing-unknown"))

    except Exception as e:
        logger.error(f"Error while processing document for user_id={user_id}: {e}", exc_info=True)
        final_response = localizer.format_value("error-doc-processing-general")
    finally:
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try: await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError): pass

    reply_markup = None
    if failed_prompt_for_retry:
        await state.update_data({LAST_FAILED_PROMPT_KEY: failed_prompt_for_retry})
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value('button-retry-request')
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False
    try:
        MAX_RESPONSE_LEN = 4000
        if len(final_response) > MAX_RESPONSE_LEN:
            cutoff_msg = localizer.format_value("response-truncated")
            final_response = final_response[:MAX_RESPONSE_LEN] + f"\n\n{cutoff_msg}"

        await status_message.edit_text(final_response, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
             logger.debug(f"Message {status_message.message_id} (document) is not modified.")
        elif "can't parse entities" in str(e) or "nested entities" in str(e):
            logger.warning(f"Error HTML parsing after document for user_id={user_id}. Sending plain text. Error: {e}")
            try:
                await status_message.edit_text(final_response, parse_mode=None, reply_markup=reply_markup)
            except Exception as fallback_e:
                logger.error(f"Can't send text after document plain text for user_id={user_id}: {fallback_e}", exc_info=True)
                error_msg = localizer.format_value('error-display')
                await status_message.edit_text(error_msg)
                save_needed = False
        else:
            logger.error(f"Unexpected error TelegramBadRequest after document for user_id={user_id}: {e}", exc_info=True)
            error_msg = localizer.format_value('error-telegram-send')
            await status_message.edit_text(error_msg)
            save_needed = False
    except Exception as e:
        logger.error(f"General error while editing message after document for user_id={user_id}: {e}", exc_info=True)
        error_msg = localizer.format_value('error-general')
        await status_message.edit_text(error_msg)
        save_needed = False

    if save_needed and updated_history:
        await save_history(user_id, updated_history)