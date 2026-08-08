"""
services/extraction/pdf.py — PDF Extractor.

Uses PyMuPDF (fitz) to extract text page-by-page from a PDF file.
Pages with fewer than 50 extractable characters are skipped with a
warning log (typically scanned/image-only pages).
"""

import logging
from typing import List

import fitz  # PyMuPDF

from models.schemas import TextSegment

logger = logging.getLogger(__name__)

_MIN_CHARS = 50


def extract_pdf(file_bytes: bytes) -> List[TextSegment]:
    """
    Extract text from a PDF file, one TextSegment per page.

    Each segment carries a 1-based page number in its `location` field.
    Pages with fewer than 50 extractable characters (e.g. scanned pages)
    are skipped and a warning is logged with the 1-based page number.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        List of TextSegment objects, one per extractable page.
    """
    segments: List[TextSegment] = []

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page_index, page in enumerate(doc):
            page_number = page_index + 1  # 1-based
            page_text = page.get_text()

            if len(page_text.strip()) < _MIN_CHARS:
                logger.warning(
                    "PDF page %d has fewer than %d extractable characters — skipping.",
                    page_number,
                    _MIN_CHARS,
                )
                continue

            segments.append(TextSegment(text=page_text, location=page_number))

    return segments
