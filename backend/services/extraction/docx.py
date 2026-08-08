"""
services/extraction/docx.py — DOCX Extractor.

Uses python-docx to extract text paragraph-by-paragraph from a DOCX file.
Paragraphs that contain no non-whitespace text are skipped.
Each segment's `location` is set to ceil(paragraph_index / 10), where
paragraph_index is the 1-based ordinal of the paragraph in document order.
"""

import io
import logging
import math
from typing import List

from docx import Document

from models.schemas import TextSegment

logger = logging.getLogger(__name__)


def extract_docx(file_bytes: bytes) -> List[TextSegment]:
    """
    Extract text from a DOCX file, one TextSegment per paragraph.

    Each segment's `location` is set to ceil(paragraph_index / 10),
    where paragraph_index is the 1-based ordinal of the paragraph in
    document order.  Empty/whitespace-only paragraphs are skipped.

    Args:
        file_bytes: Raw bytes of the DOCX file.

    Returns:
        List of TextSegment objects, one per non-empty paragraph.
    """
    segments: List[TextSegment] = []

    doc = Document(io.BytesIO(file_bytes))

    paragraph_index = 0  # incremented only for non-empty paragraphs
    for raw_index, paragraph in enumerate(doc.paragraphs, start=1):
        text = paragraph.text
        if not text.strip():
            logger.debug(
                "DOCX paragraph %d is empty — skipping.",
                raw_index,
            )
            continue

        paragraph_index += 1
        location = math.ceil(paragraph_index / 10)
        segments.append(TextSegment(text=text, location=location))

    logger.info(
        "DOCX extraction complete: %d non-empty paragraphs extracted.",
        len(segments),
    )
    return segments
