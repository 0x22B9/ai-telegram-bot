import logging
from typing import Any, Dict, Optional, Tuple

from fluent.runtime import FluentLocalization

from .document_parser import (
    PARSING_EMPTY_DOC,
    PARSING_ERROR_DOCX,
    PARSING_ERROR_PDF,
    PARSING_ERROR_TXT,
    PARSING_LIB_MISSING,
    PARSING_SUCCESS,
    PARSING_UNSUPPORTED_TYPE,
)
from .gemini import (
    GEMINI_API_KEY_ERROR,
    GEMINI_API_KEY_INVALID,
    GEMINI_BLOCKED_ERROR,
    GEMINI_QUOTA_ERROR,
    GEMINI_REQUEST_ERROR,
    GEMINI_SERVICE_UNAVAILABLE,
    GEMINI_TRANSCRIPTION_ERROR,
    GEMINI_UNKNOWN_API_ERROR,
    IMAGE_ANALYSIS_ERROR,
)
from .image_generation import (
    IMAGE_GEN_API_ERROR,
    IMAGE_GEN_CONNECTION_ERROR,
    IMAGE_GEN_CONTENT_FILTER_ERROR,
    IMAGE_GEN_RATE_LIMIT_ERROR,
    IMAGE_GEN_SUCCESS,
    IMAGE_GEN_TIMEOUT_ERROR,
    IMAGE_GEN_UNKNOWN_ERROR,
)

DEFAULT_ERROR_KEY = "error-general"
FTL_ARGS_SEPARATOR = "|"

TELEGRAM_DOWNLOAD_ERROR = "TELEGRAM_DOWNLOAD_ERROR"
TELEGRAM_UPLOAD_ERROR = "TELEGRAM_UPLOAD_ERROR"
TELEGRAM_NETWORK_ERROR = "TELEGRAM_NETWORK_ERROR"
TELEGRAM_MESSAGE_DELETED_ERROR = "TELEGRAM_MESSAGE_DELETED_ERROR"
DATABASE_SAVE_ERROR = "DATABASE_SAVE_ERROR"
PARSING_ERROR_UNKNOWN = "PARSING_ERROR_UNKNOWN"

RETRYABLE_ERRORS = {
    GEMINI_REQUEST_ERROR,
    GEMINI_SERVICE_UNAVAILABLE,
    IMAGE_GEN_TIMEOUT_ERROR,
    IMAGE_GEN_RATE_LIMIT_ERROR,
    IMAGE_GEN_CONNECTION_ERROR,
    IMAGE_ANALYSIS_ERROR,
    GEMINI_TRANSCRIPTION_ERROR,
    TELEGRAM_NETWORK_ERROR,
}

ERROR_CODE_TO_FTL_KEY: Dict[str, str] = {
    GEMINI_QUOTA_ERROR: "error-quota-exceeded",
    GEMINI_API_KEY_ERROR: "error-gemini-api-key",
    GEMINI_API_KEY_INVALID: "error-gemini-api-key-invalid",
    GEMINI_BLOCKED_ERROR: "error-blocked-content",
    GEMINI_REQUEST_ERROR: "error-gemini-request",
    GEMINI_SERVICE_UNAVAILABLE: "error-gemini-service-unavailable",
    GEMINI_UNKNOWN_API_ERROR: "error-gemini-unknown",
    IMAGE_ANALYSIS_ERROR: "error-image-analysis-failed",
    GEMINI_TRANSCRIPTION_ERROR: "error-transcription-failed",
    IMAGE_GEN_API_ERROR: "error-image-api_error",
    IMAGE_GEN_TIMEOUT_ERROR: "error-image-timeout_error",
    IMAGE_GEN_RATE_LIMIT_ERROR: "error-image-rate_limit_error",
    IMAGE_GEN_CONTENT_FILTER_ERROR: "error-image-content_filter_error",
    IMAGE_GEN_CONNECTION_ERROR: "error-image-connection-error",
    IMAGE_GEN_UNKNOWN_ERROR: "error-image-unknown",
    PARSING_UNSUPPORTED_TYPE: "error-doc-unsupported-type",
    PARSING_ERROR_PDF: "error-doc-parsing-pdf",
    PARSING_ERROR_DOCX: "error-doc-parsing-docx",
    PARSING_ERROR_TXT: "error-doc-parsing-txt",
    PARSING_LIB_MISSING: "error-doc-parsing-lib_missing",
    PARSING_EMPTY_DOC: "error-doc-parsing-emptydoc",
    PARSING_ERROR_UNKNOWN: "error-doc-parsing-unknown",
    TELEGRAM_DOWNLOAD_ERROR: "error-telegram-download",
    TELEGRAM_UPLOAD_ERROR: "error-telegram-upload",
    TELEGRAM_NETWORK_ERROR: "error-telegram-network",
    TELEGRAM_MESSAGE_DELETED_ERROR: "error-message-deleted",
    DATABASE_SAVE_ERROR: "error-db-save",
}

logger = logging.getLogger(__name__)


def format_error_message(
    error_code_with_details: Optional[str],
    localizer: FluentLocalization,
    default_fallback_key: str = DEFAULT_ERROR_KEY,
) -> Tuple[str, bool]:
    """
    Formats an error message to the user based on the error code.

    Args:
        error_code_with_details: Error code, possibly with details after ':' (e.g. "GEMINI_BLOCKED_ERROR:HATE_SPEECH").
                                                                             OR special code with arguments for FTL after '|' (e.g. "PARSING_UNSUPPORTED_TYPE|mime_type=text/csv")
        localizer: FluentLocalization instance.
        default_fallback_key: FTL key for use, if error code unknown.

    Returns:
        Tuple (message_for_user: str, offer_retry: bool)
    """
    if not error_code_with_details:
        return localizer.format_value(default_fallback_key), False

    ftl_args: Optional[Dict[str, Any]] = None
    if FTL_ARGS_SEPARATOR in error_code_with_details:
        parts = error_code_with_details.split(FTL_ARGS_SEPARATOR, 1)
        error_code = parts[0]
        try:
            ftl_args = dict(item.split("=") for item in parts[1].split(","))
        except ValueError:
            logger.warning(f"Could not parse FTL args: {parts[1]}")
    else:
        error_code = error_code_with_details

    details: Optional[str] = None
    if ":" in error_code:
        parts = error_code.split(":", 1)
        base_error_code = parts[0]
        details = parts[1]
    else:
        base_error_code = error_code

    ftl_key = ERROR_CODE_TO_FTL_KEY.get(base_error_code)
    needs_retry = base_error_code in RETRYABLE_ERRORS

    if ftl_args is None:
        if base_error_code == GEMINI_BLOCKED_ERROR and details:
            ftl_args = {"reason": details}
        elif base_error_code == GEMINI_REQUEST_ERROR and details:
            ftl_args = {"error": details}
        elif base_error_code == IMAGE_ANALYSIS_ERROR and details:
            ftl_args = {"error": details}
        elif base_error_code == GEMINI_TRANSCRIPTION_ERROR and details:
            ftl_args = {"error": details}
        elif base_error_code == PARSING_LIB_MISSING and details:
            ftl_args = {"library": details}

    try:
        message = localizer.format_value(ftl_key, args=ftl_args)
    except Exception as format_exc:
        logger.warning(
            f"Could not format FTL key '{ftl_key}' with args {ftl_args} (Error: {format_exc}). Falling back to default '{default_fallback_key}'."
        )
        message = localizer.format_value(default_fallback_key)

    return message, needs_retry
