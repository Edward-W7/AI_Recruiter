import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Union

import PyPDF2
import docx


def extract_text_from_pdf(path: Union[str, Path]) -> str:
    """
    Extract all text from a PDF file, handling encrypted PDFs gracefully.
    """
    reader = PyPDF2.PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt('')
        except Exception:
            return ''

    texts = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ''
        except Exception:
            page_text = ''
        texts.append(page_text)
    return "\n".join(texts)


import win32com.client
from pathlib import Path

def extract_text_from_docx(path):
    full_path = Path(path).resolve()
    if not full_path.exists():
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
        doc.Close(False)
    finally:
        word.Quit()

    return text


def extract_text_from_doc(path: Union[str, Path]) -> str:
    """
    Extract all text from a legacy .doc file using Windows COM.
    """
    from pathlib import Path
    import win32com.client  # requires pywin32

    full_path = Path(path).resolve()
    if not full_path.exists():
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
        doc.Close(False)
    finally:
        word.Quit()

    return text

def extract_text_from_txt(path: Union[str, Path]) -> str:
    """
    Read text from a plain .txt file.
    """
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def extract_resumes_text(folder: Union[str, Path]) -> Dict[str, str]:
    """
    Recursively iterate over all files in folder and extract text from each resume.
    Supported formats: .pdf, .docx, .doc, .txt
    Returns a mapping of relative file paths to extracted content.
    """
    base = Path(folder)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Resumes folder not found: {base}")

    texts: Dict[str, str] = {}
    for file_path in base.rglob('*'):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
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
                continue
        except Exception as e:
            content = f"Error extracting text: {e}"
        rel = file_path.relative_to(base)
        texts[str(rel)] = content
    return texts


def parse_documents(document_folder: Path) -> Dict[str, str]:
    """
    Convenience wrapper: calls extract_resumes_text and returns its result.
    """
    return extract_resumes_text(document_folder)


if __name__ == '__main__':
    import json
    import sys

    folder = Path('job_documents')
    try:
        results = parse_documents(folder)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
