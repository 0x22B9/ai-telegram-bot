import asyncio
import io
import logging
from typing import Optional

from aiogram import Bot, F, Router, types
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluent.runtime import FluentLocalization

from src.db import save_history
from src.handlers.text import (
    LAST_FAILED_PROMPT_KEY,
    RETRY_CALLBACK_DATA,
    _process_text_input,
    send_typing_periodically,
)
from src.keyboards import get_main_keyboard
from src.services import document_parser as doc_parser
from src.services.errors import (
    DATABASE_SAVE_ERROR,
    PARSING_LIB_MISSING,
    TELEGRAM_DOWNLOAD_ERROR,
    TELEGRAM_MESSAGE_DELETED_ERROR,
    TELEGRAM_NETWORK_ERROR,
    format_error_message,
)

logger = logging.getLogger(__name__)
document_router = Router()

MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024
MAX_PROMPT_LENGTH_FOR_AI = 30000


@document_router.message(F.document, StateFilter(None))
async def handle_document_message(
    message: types.Message, state: FSMContext, bot: Bot, localizer: FluentLocalization
):
    user_id = message.from_user.id
    chat_id = message.chat.id
    document = message.document

    mime_type = document.mime_type
    if mime_type not in doc_parser.SUPPORTED_MIME_TYPES:
        logger.info(
            f"Got unsupported document from user_id={user_id}, mime_type={mime_type}, filename={document.file_name}"
        )
        error_code_with_arg = f"{doc_parser.PARSING_UNSUPPORTED_TYPE}{doc_parser.FTL_ARGS_SEPARATOR}mime_type={mime_type}"
        error_text, _ = format_error_message(error_code_with_arg, localizer)
        await message.reply(error_text)
        return

    if document.file_size > MAX_DOCUMENT_SIZE_BYTES:
        logger.warning(
            f"Document from user_id={user_id} is too large: {document.file_size / (1024 * 1024):.2f} MB"
        )
        limit_mb_str = f"{MAX_DOCUMENT_SIZE_BYTES / (1024 * 1024):.0f}"
        error_code_with_arg = (
            f"DOC_TOO_LARGE{doc_parser.FTL_ARGS_SEPARATOR}limit_mb={limit_mb_str}"
        )
        error_text = localizer.format_value(
            "error-doc-too-large", args={"limit_mb": limit_mb_str}
        )
        await message.reply(error_text)
        return

    logger.info(
        f"Got document from user_id={user_id}: mime_type={mime_type}, filename={document.file_name}, size={document.file_size}"
    )

    processing_doc_text = localizer.format_value(
        "processing-document", args={"filename": document.file_name or "document"}
    )
    status_message = await message.answer(processing_doc_text)
    typing_task = asyncio.create_task(send_typing_periodically(bot, chat_id))

    extracted_text: Optional[str] = None
    parsing_error_code: Optional[str] = None
    final_response: str = localizer.format_value("error-general")
    updated_history = None
    failed_prompt_for_retry = None
    save_needed = False
    doc_bytes_io = io.BytesIO()

    try:
        logger.debug(f"Starting download of document {document.file_id}...")
        await bot.download(file=document, destination=doc_bytes_io)
        doc_bytes = doc_bytes_io.getvalue()
        if not doc_bytes:
            raise ValueError("Downloaded document bytes are empty.")
        logger.debug(
            f"Document {document.file_id} downloaded ({len(doc_bytes)} bytes)."
        )

        (
            extracted_text,
            parsing_error_code,
        ) = await doc_parser.extract_text_from_document(
            file_bytes=doc_bytes, mime_type=mime_type
        )

        if extracted_text and parsing_error_code == doc_parser.PARSING_SUCCESS:
            logger.info(
                f"Text from document {document.file_name} extracted ({len(extracted_text)} symbols)."
            )
            processing_text_status = localizer.format_value(
                "processing-extracted-text",
                args={"filename": document.file_name or "document"},
            )
            try:
                await status_message.edit_text(processing_text_status)
            except Exception as e_edit_status:
                logger.warning(
                    f"Could not edit status message for document processing: {e_edit_status}"
                )

            safe_filename = document.file_name or "document"
            prompt_intro = localizer.format_value(
                "prompt-analyze-document", args={"filename": safe_filename}
            )
            user_input_for_gemini = f"{prompt_intro}\n\n{extracted_text}"

            if len(user_input_for_gemini) > MAX_PROMPT_LENGTH_FOR_AI:
                logger.warning(
                    f"Extracted text for user {user_id} is too long ({len(user_input_for_gemini)}), truncating for AI."
                )
                truncation_marker = localizer.format_value(
                    "response-text-truncated-for-ai"
                )
                allowed_text_length = (
                    MAX_PROMPT_LENGTH_FOR_AI
                    - len(prompt_intro)
                    - len(truncation_marker)
                    - 5
                )
                if allowed_text_length < 0:
                    allowed_text_length = 0

                truncated_extracted_text = extracted_text[:allowed_text_length]
                user_input_for_gemini = (
                    f"{prompt_intro}\n\n{truncated_extracted_text}{truncation_marker}"
                )

            (
                final_response,
                updated_history,
                failed_prompt_for_retry,
            ) = await _process_text_input(
                user_text=user_input_for_gemini,
                user_id=user_id,
                state=state,
                localizer=localizer,
            )
            save_needed = (
                updated_history is not None and failed_prompt_for_retry is None
            )

        else:
            logger.warning(
                f"Text extraction error from document {document.file_name} for user_id={user_id}: {parsing_error_code}"
            )
            error_code_to_format = parsing_error_code
            if parsing_error_code == PARSING_LIB_MISSING:
                error_lib = "pypdf" if mime_type == "application/pdf" else "python-docx"
                error_code_to_format = f"{PARSING_LIB_MISSING}{doc_parser.FTL_ARGS_SEPARATOR}library={error_lib}"

            final_response, _ = format_error_message(
                error_code_to_format, localizer, "error-doc-parsing-unknown"
            )
            save_needed = False

    except (TelegramNetworkError, TelegramBadRequest, ValueError, Exception) as e:
        if isinstance(e, (TelegramNetworkError, TelegramBadRequest)):
            logger.error(
                f"Failed to download document {document.file_id} for user {user_id}: {e}",
                exc_info=True,
            )
            final_response, _ = format_error_message(TELEGRAM_DOWNLOAD_ERROR, localizer)
        elif isinstance(e, ValueError):
            logger.error(
                f"Downloaded document {document.file_id} for user {user_id} was empty."
            )
            final_response, _ = format_error_message(TELEGRAM_DOWNLOAD_ERROR, localizer)
        else:
            logger.exception(
                f"Unexpected error processing document for user_id={user_id}"
            )
            final_response, _ = format_error_message(None, localizer)
        save_needed = False
        failed_prompt_for_retry = None
    finally:
        doc_bytes_io.close()
        if typing_task and not typing_task.done():
            typing_task.cancel()
            try:
                await asyncio.wait_for(typing_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    reply_markup = None
    if failed_prompt_for_retry:
        await state.update_data({LAST_FAILED_PROMPT_KEY: failed_prompt_for_retry})
        builder = InlineKeyboardBuilder()
        retry_button_text = localizer.format_value("button-retry-request")
        builder.button(text=retry_button_text, callback_data=RETRY_CALLBACK_DATA)
        reply_markup = builder.as_markup()
        save_needed = False

    message_sent_or_edited = False
    try:
        MAX_RESPONSE_LEN = 4000
        if len(final_response) > MAX_RESPONSE_LEN:
            cutoff_msg = localizer.format_value("response-truncated")
            final_response = (
                final_response[: MAX_RESPONSE_LEN - len(cutoff_msg) - 5]
                + f"\n\n{cutoff_msg}"
            )

        await status_message.edit_text(final_response, reply_markup=reply_markup)
        message_sent_or_edited = True
    except TelegramRetryAfter as e:
        logger.warning(
            f"Document Handler: Flood control for user {user_id}: retry after {e.retry_after}s"
        )
        await asyncio.sleep(e.retry_after)
        try:
            await status_message.edit_text(final_response, reply_markup=reply_markup)
            message_sent_or_edited = True
        except Exception as retry_e:
            logger.error(
                f"Document Handler: Failed edit after RetryAfter for user {user_id}: {retry_e}"
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(
                f"Document Handler: Message {status_message.message_id} not modified."
            )
            message_sent_or_edited = True
        elif "message to edit not found" in str(e).lower():
            logger.warning(
                f"Document Handler: Message {status_message.message_id} not found for user {user_id}. Sending new."
            )
            try:
                main_kbd = get_main_keyboard(localizer)
                await message.answer(
                    final_response, reply_markup=reply_markup or main_kbd
                )
                message_sent_or_edited = True
            except Exception as send_e:
                logger.error(
                    f"Document Handler: Failed send new message for user {user_id}: {send_e}"
                )
        elif "can't parse entities" in str(e) or "nested entities" in str(e):
            logger.warning(
                f"Document Handler: Parse error for user_id={user_id}. Plain text. Error: {e}"
            )
            try:
                await status_message.edit_text(
                    final_response, parse_mode=None, reply_markup=reply_markup
                )
                message_sent_or_edited = True
            except Exception as fallback_e:
                logger.error(
                    f"Document Handler: Failed send plain text for user_id={user_id}: {fallback_e}",
                    exc_info=True,
                )
                try:
                    await status_message.edit_text(
                        localizer.format_value("error-display")
                    )
                except Exception:
                    pass
        else:
            logger.error(
                f"Document Handler: Unexpected TelegramBadRequest for user_id={user_id}: {e}",
                exc_info=True,
            )
            try:
                await status_message.edit_text(
                    localizer.format_value("error-telegram-send")
                )
            except Exception:
                pass
    except TelegramNetworkError as e:
        logger.error(
            f"Document Handler: Network error editing message for user {user_id}: {e}"
        )
        try:
            err_msg_net, _ = format_error_message(TELEGRAM_NETWORK_ERROR, localizer)
            await status_message.edit_text(err_msg_net)
        except Exception:
            pass
    except Exception as e:
        logger.exception(
            f"Document Handler: Failed edit final response for user_id={user_id}: {e}"
        )
        try:
            await status_message.edit_text(localizer.format_value("error-general"))
        except Exception:
            pass

    if save_needed and updated_history is not None and message_sent_or_edited:
        try:
            await save_history(user_id, updated_history)
        except Exception as db_save_e:
            logger.exception(
                f"Document Handler: Failed to save history for user_id={user_id} to DB: {db_save_e}"
            )
            try:
                err_msg_db, _ = format_error_message(DATABASE_SAVE_ERROR, localizer)
                await message.answer(err_msg_db)
            except Exception as db_err_send_e:
                logger.error(
                    f"Document Handler: Failed send DB save error message to user {user_id}: {db_err_send_e}"
                )
    elif save_needed and updated_history is None:
        logger.error(
            f"Document Handler: save_needed is True, but updated_history is None for user_id={user_id}!"
        )
