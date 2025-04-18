import logging
import io
from typing import Tuple, Optional
import pypdf
import docx

logger = logging.getLogger(__name__)

# Коды ошибок парсинга
PARSING_SUCCESS = "PARSING_SUCCESS"
PARSING_UNSUPPORTED_TYPE = "PARSING_UNSUPPORTED_TYPE"
PARSING_ERROR_PDF = "PARSING_ERROR_PDF"
PARSING_ERROR_DOCX = "PARSING_ERROR_DOCX"
PARSING_ERROR_TXT = "PARSING_ERROR_TXT"
PARSING_LIB_MISSING = "PARSING_LIB_MISSING"
PARSING_EMPTY_DOC = "PARSING_EMPTY_DOC"

SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "docx",
    "text/plain": "txt",
}

async def extract_text_from_document(
    file_bytes: bytes,
    mime_type: str
) -> Tuple[Optional[str], str]:
    """
    Извлекает текст из байтов документа (PDF, DOCX или TXT).
    Возвращает кортеж (extracted_text | None, status_code).
    """
    file_ext = SUPPORTED_MIME_TYPES.get(mime_type)

    if not file_ext:
        logger.warning(f"Попытка обработать неподдерживаемый mime_type: {mime_type}")
        return None, PARSING_UNSUPPORTED_TYPE

    extracted_text = ""
    bytes_io = io.BytesIO(file_bytes)

    try:
        if file_ext == "pdf":
            if not pypdf:
                logger.error("pypdf не установлен, не могу обработать PDF.")
                return None, PARSING_LIB_MISSING
            try:
                reader = pypdf.PdfReader(bytes_io)
                logger.info(f"Начинаю извлечение текста из PDF ({len(reader.pages)} страниц)...")
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                    except Exception as page_err:
                        # Логгируем ошибку конкретной страницы, но продолжаем
                        logger.warning(f"Ошибка извлечения текста со страницы {i+1} PDF: {page_err}", exc_info=False)
                logger.info(f"Извлечение текста из PDF завершено ({len(extracted_text)} символов).")
            except pypdf.errors.PdfReadError as e:
                logger.error(f"Ошибка чтения PDF (возможно, зашифрован или поврежден): {e}")
                return None, PARSING_ERROR_PDF # Ошибка чтения файла
            except Exception as e:
                logger.error(f"Общая ошибка при обработке PDF: {e}", exc_info=True)
                return None, PARSING_ERROR_PDF

        elif file_ext == "docx":
            if not docx:
                logger.error("python-docx не установлен, не могу обработать DOCX.")
                return None, PARSING_LIB_MISSING
            try:
                logger.info("Начинаю извлечение текста из DOCX...")
                document = docx.Document(bytes_io)
                for para in document.paragraphs:
                    extracted_text += para.text + "\n"
                logger.info(f"Извлечение текста из DOCX завершено ({len(extracted_text)} символов).")
            except Exception as e:
                logger.error(f"Ошибка при обработке DOCX: {e}", exc_info=True)
                return None, PARSING_ERROR_DOCX

        elif file_ext == "txt":
            logger.info("Начинаю извлечение текста из TXT...")
            try:
                # Пытаемся декодировать как UTF-8 (самая частая кодировка)
                extracted_text = file_bytes.decode('utf-8')
                logger.info(f"Извлечение текста из TXT (UTF-8) завершено ({len(extracted_text)} символов).")
            except UnicodeDecodeError:
                logger.warning("Не удалось декодировать TXT как UTF-8, пробую cp1251...")
                try:
                    # Пробуем другую популярную кодировку для русского текста
                    extracted_text = file_bytes.decode('cp1251')
                    logger.info(f"Извлечение текста из TXT (cp1251) завершено ({len(extracted_text)} символов).")
                except Exception as e_decode:
                    logger.error(f"Ошибка декодирования TXT файла: {e_decode}", exc_info=True)
                    return None, PARSING_ERROR_TXT # Ошибка декодирования
            except Exception as e:
                 logger.error(f"Общая ошибка при обработке TXT: {e}", exc_info=True); return None, PARSING_ERROR_TXT
        # ----------------------------------

        # Проверяем, извлекли ли мы что-нибудь
        if not extracted_text.strip():
            logger.warning(f"Документ ({mime_type}) не содержит извлекаемого текста или пуст.")
            return None, PARSING_EMPTY_DOC

        return extracted_text.strip(), PARSING_SUCCESS

    except Exception as e:
        logger.error(f"Неожиданная ошибка при подготовке к парсингу {mime_type}: {e}", exc_info=True)
        if file_ext == "pdf": return None, PARSING_ERROR_PDF
        if file_ext == "docx": return None, PARSING_ERROR_DOCX
        if file_ext == "txt": return None, PARSING_ERROR_TXT # <<< Добавлено
        return None, PARSING_UNSUPPORTED_TYPE
    finally:
        # Закрываем BytesIO только если он был создан (он создается всегда в начале)
        if 'bytes_io' in locals() and bytes_io:
            bytes_io.close()