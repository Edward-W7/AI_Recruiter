import sys
from pathlib import Path
from typing import Dict, Union

import PyPDF2
import docx


def extract_text_from_pdf(path: Union[str, Path]) -> str:
    """
    Extract all text from a PDF file.
    """
    reader = PyPDF2.PdfReader(str(path))
    text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)
    return "\n".join(text)


def extract_text_from_docx(path: Union[str, Path]) -> str:
    """
    Extract all text from a .docx file.
    """
    doc = docx.Document(str(path))
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return "\n".join(text)


def extract_text_from_txt(path: Union[str, Path]) -> str:
    """
    Read text from a plain .txt file.
    """
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def extract_resumes_text(
    folder: Union[str, Path]
) -> Dict[str, str]:
    """
    Recursively iterate over all files in `folder` (including subdirectories)
    and extract text from each resume.
    Supported formats: .pdf, .docx, .txt

    Returns:
        Dict mapping relative file paths (within `folder`) to their extracted text.
    """
    folder = Path(folder)
    texts: Dict[str, str] = {}

    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Resumes folder not found: {folder}")

    # Walk through all nested files
    for file_path in folder.rglob('*'):
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()
        try:
            if suffix == '.pdf':
                content = extract_text_from_pdf(file_path)
            elif suffix == '.docx':
                content = extract_text_from_docx(file_path)
            elif suffix == '.txt':
                content = extract_text_from_txt(file_path)
            else:
                # skip unsupported formats
                continue

            # store relative path key for clarity
            rel_path = file_path.relative_to(folder)
            texts[str(rel_path)] = content

        except Exception as e:
            texts[str(file_path.relative_to(folder))] = f"Error extracting text: {e}"

    return texts


def parse_resumes(resume_folder: Path) -> Dict[str, str]:
    """
    Convenience wrapper: calls extract_resumes_text and returns its result.

    Args:
        resume_folder: Path to the base folder containing resume subfolders.

    Returns:
        Dict[str, str]: mapping of relative file paths to extracted text.
    """
    return extract_resumes_text(resume_folder)


if __name__ == '__main__':
    import json


    folder = Path("resumes")
    try:
        results = parse_resumes(folder)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
