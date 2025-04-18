import logging
import io
from typing import Tuple, Optional
import pypdf
import docx

logger = logging.getLogger(__name__)

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
    "text/plain": "txt",
}

async def extract_text_from_document(
    file_bytes: bytes,
    mime_type: str
) -> Tuple[Optional[str], str]:
    """
    Extracts text from a document (PDF, DOCX or TXT).
    Returns tuple (extracted_text | None, status_code).
    """
    file_ext = SUPPORTED_MIME_TYPES.get(mime_type)

    if not file_ext:
        logger.warning(f"Trying to parse unsupported mime_type: {mime_type}")
        return None, PARSING_UNSUPPORTED_TYPE

    extracted_text = ""
    bytes_io = io.BytesIO(file_bytes)

    try:
        if file_ext == "pdf":
            if not pypdf:
                logger.error("pypdf not installed, can't parse PDF.")
                return None, PARSING_LIB_MISSING
            try:
                reader = pypdf.PdfReader(bytes_io)
                logger.info(f"Starting to extract text from PDF ({len(reader.pages)} pages)...")
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                    except Exception as page_err:
                        logger.warning(f"Error extracting text from page {i+1} PDF: {page_err}", exc_info=False)
                logger.info(f"Extracing text from PDF completed ({len(extracted_text)} symbols).")
            except (pypdf.errors.PdfReadError, Exception) as e:
                logger.error(f"Error reading PDF (maybe, corrupted or encrypted): {e}")
                return None, PARSING_ERROR_PDF
            except Exception as e:
                logger.error(f"General error while parsing PDF: {e}", exc_info=True)
                return None, PARSING_ERROR_PDF

        elif file_ext == "docx":
            if not docx:
                logger.error("python-docx not installed, can't parse DOCX.")
                return None, PARSING_LIB_MISSING
            try:
                logger.info("Starting to extract text from DOCX...")
                document = docx.Document(bytes_io)
                for para in document.paragraphs:
                    extracted_text += para.text + "\n"
                logger.info(f"Extracing text from DOCX completed ({len(extracted_text)} symbols).")
            except Exception as e:
                logger.error(f"Error while parsing DOCX: {e}", exc_info=True)
                return None, PARSING_ERROR_DOCX

        elif file_ext == "txt":
            logger.info("Starting to extract text from TXT...")
            try:
                extracted_text = file_bytes.decode('utf-8')
                logger.info(f"Extracing text from TXT (UTF-8) completed ({len(extracted_text)} symbols).")
            except UnicodeDecodeError:
                logger.warning("Can't decode TXT with UTF-8, trying cp1251...")
                try:
                    extracted_text = file_bytes.decode('cp1251')
                    logger.info(f"Extracing text from TXT (cp1251) completed ({len(extracted_text)} symbols).")
                except Exception as e_decode:
                    logger.error(f"Error while decoding TXT: {e_decode}", exc_info=True)
                    return None, PARSING_ERROR_TXT
            except Exception as e:
                 logger.error(f"General error while parsing TXT: {e}", exc_info=True); return None, PARSING_ERROR_TXT

        if not extracted_text.strip():
            logger.warning(f"Document ({mime_type}) is empty or doesn't contain any text.")
            return None, PARSING_EMPTY_DOC

        return extracted_text.strip(), PARSING_SUCCESS

    except Exception as e:
        logger.error(f"Unexpected error while parsing {mime_type}: {e}", exc_info=True)
        if file_ext == "pdf": return None, PARSING_ERROR_PDF
        if file_ext == "docx": return None, PARSING_ERROR_DOCX
        if file_ext == "txt": return None, PARSING_ERROR_TXT
        return None, PARSING_UNSUPPORTED_TYPE
    finally:
        if 'bytes_io' in locals() and bytes_io:
            bytes_io.close()