import logging
import sys
from pathlib import Path
from typing import Dict, Union

import PyPDF2
import win32com.client

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(path: Union[str, Path]) -> str:
    """
    Extract all text from a PDF file, handling encrypted PDFs gracefully.
    """
    full_path = Path(path)
    logger.info("Extracting PDF text from %s", full_path)
    try:
        reader = PyPDF2.PdfReader(str(full_path))
    except Exception as e:
        logger.error("Failed to open PDF %s: %s", full_path, e)
        return ""

    if reader.is_encrypted:
        try:
            reader.decrypt('')
            logger.debug("Decrypted PDF %s successfully", full_path)
        except Exception as e:
            logger.warning("Could not decrypt PDF %s: %s", full_path, e)
            return ""

    texts = []
    for i, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ''
        except Exception as e:
            logger.warning("Error extracting text from page %d of %s: %s", i, full_path, e)
            page_text = ''
        texts.append(page_text)
    return "\n".join(texts)


def extract_text_from_docx(path: Union[str, Path]) -> str:
    """
    Extract all text from a .docx file using COM, including all parts.
    """
    full_path = Path(path).resolve()
    logger.info("Extracting DOCX text via COM from %s", full_path)
    if not full_path.exists():
        logger.error("DOCX file not found: %s", full_path)
        raise FileNotFoundError(full_path)

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False

    try:
        doc = word.Documents.Open(
            FileName=str(full_path),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False
        )
        text = doc.Content.Text
        logger.debug("Successfully extracted DOCX content from %s", full_path)
        doc.Close(False)
    except Exception as e:
        logger.error("COM error extracting DOCX %s: %s", full_path, e)
        text = ""
    finally:
        try:
            word.Quit()
        except Exception as e:
            logger.warning("Failed to quit Word COM for %s: %s", full_path, e)

    return text


def extract_text_from_doc(path: Union[str, Path]) -> str:
    """
    Extract all text from a legacy .doc file using Windows COM.
    """
    full_path = Path(path).resolve()
    logger.info("Extracting legacy DOC text via COM from %s", full_path)
    if not full_path.exists():
        logger.error(".doc file not found: %s", full_path)
        raise FileNotFoundError(f".doc file not found: {full_path}")

    word = win32com.client.Dispatch('Word.Application')
    word.Visible = False
    word.DisplayAlerts = False

    try:
        doc = word.Documents.Open(
            FileName=str(full_path),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False
        )
        text = doc.Content.Text
        logger.debug("Successfully extracted .doc content from %s", full_path)
        doc.Close(False)
    except Exception as e:
        logger.error("COM error extracting .doc %s: %s", full_path, e)
        text = ""
    finally:
        try:
            word.Quit()
        except Exception as e:
            logger.warning("Failed to quit Word COM for %s: %s", full_path, e)

    return text


def extract_text_from_txt(path: Union[str, Path]) -> str:
    """
    Read text from a plain .txt file.
    """
    full_path = Path(path)
    logger.info("Reading TXT file %s", full_path)
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error("Error reading text file %s: %s", full_path, e)
        return ""


def extract_resumes_text(folder: Union[str, Path]) -> Dict[str, str]:
    """
    Recursively iterate over all files in folder and extract text from each resume.
    Supported formats: .pdf, .docx, .doc, .txt
    Returns a mapping of relative file paths to extracted content.
    """
    base = Path(folder)
    logger.info("Scanning folder for resumes: %s", base)
    if not base.exists() or not base.is_dir():
        logger.error("Resumes folder not found or is not a directory: %s", base)
        raise FileNotFoundError(f"Resumes folder not found: {base}")

    texts: Dict[str, str] = {}
    for file_path in base.rglob('*'):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(base)
        suffix = file_path.suffix.lower()
        logger.debug("Processing file %s (suffix %s)", file_path, suffix)
        try:
            if suffix == '.pdf':
                content = extract_text_from_pdf(file_path)
            elif suffix == '.docx':
                content = extract_text_from_docx(file_path)
            elif suffix == '.doc':
                content = extract_text_from_doc(file_path)
            elif suffix == '.txt':
                content = extract_text_from_txt(file_path)
            else:
                logger.debug("Skipping unsupported file type: %s", file_path)
                continue
        except Exception as e:
            logger.error("Error extracting text from %s: %s", file_path, e)
            content = f"Error extracting text: {e}"
        texts[str(rel)] = content

    logger.info("Extraction complete: processed %d files", len(texts))
    return texts


def parse_documents(document_folder: Path) -> Dict[str, str]:
    """
    Convenience wrapper: calls extract_resumes_text and returns its result.
    """
    logger.info("Parsing documents in folder: %s", document_folder)
    return extract_resumes_text(document_folder)


if __name__ == '__main__':
    import json

    folder = Path('job_documents')
    try:
        results = parse_documents(folder)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        logger.info("Finished parsing documents and output JSON.")
    except FileNotFoundError as e:
        logger.critical("Fatal error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
