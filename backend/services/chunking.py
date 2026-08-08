"""
services/chunking.py — Text Chunker

Splits List[TextSegment] into overlapping List[Chunk] with:
  - ≤ 500 words per chunk
  - 45–55 word overlap between consecutive chunks from the same segment
  - Paragraph-boundary splits (blank lines); sentence-boundary fallback for oversized paragraphs
  - Full metadata attachment (document_id, file_type, location)
  - Warning + skip for empty/whitespace segments

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import logging
import re
import uuid
from typing import List

from models.schemas import Chunk, FileType, TextSegment

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_WORDS = 500
OVERLAP_TARGET = 50
OVERLAP_MIN = 45
OVERLAP_MAX = 55


# ── Helpers ────────────────────────────────────────────────────────────────────

def _word_count(text: str) -> int:
    """Return the number of whitespace-delimited words in *text*."""
    return len(text.split())


def _count_words_in_parts(parts: List[str]) -> int:
    """Sum word counts across a list of text parts."""
    return sum(_word_count(p) for p in parts)


def _join_parts(parts: List[str]) -> str:
    """Join buffer parts into a single string, stripping leading/trailing whitespace."""
    return " ".join(p.strip() for p in parts if p.strip())


def _get_overlap_words(parts: List[str], target: int = OVERLAP_TARGET) -> List[str]:
    """
    Extract the last *target* words from *parts* and return them as a single
    element list (a plain string).  The actual overlap is clamped so that it
    stays within [OVERLAP_MIN, OVERLAP_MAX] when the combined text has enough
    words; if fewer words are available we just take what we have.
    """
    full_text = _join_parts(parts)
    words = full_text.split()
    total = len(words)
    if total == 0:
        return []
    take = min(target, total)
    overlap_text = " ".join(words[-take:])
    return [overlap_text]


def _split_by_blank_lines(text: str) -> List[str]:
    """Split *text* on one or more blank lines, returning non-empty paragraphs."""
    raw = re.split(r"\n\s*\n", text)
    return [p.strip() for p in raw if p.strip()]


def _split_sentences(text: str) -> List[str]:
    """
    Split *text* at sentence boundaries.
    Boundary pattern: '.', '!' or '?' followed by whitespace or end-of-string.
    Returns non-empty sentence strings.
    """
    parts = re.split(r"(?<=[.!?])(?:\s+|$)", text)
    return [p.strip() for p in parts if p.strip()]


def _emit_chunk(
    buffer: List[str],
    document_id: str,
    file_type: FileType,
    location,
) -> Chunk:
    """Create and return a Chunk from the current buffer contents."""
    text = _join_parts(buffer)
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id=document_id,
        file_type=file_type,
        text=text,
        location=location,
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def chunk_segments(
    segments: List[TextSegment],
    document_id: str,
    file_type: FileType,
) -> List[Chunk]:
    """
    Split *segments* into overlapping Chunk objects.

    Parameters
    ----------
    segments    : list of TextSegment produced by an extractor
    document_id : unique identifier for the owning document
    file_type   : FileType enum value for the owning document

    Returns
    -------
    List[Chunk] — every chunk carries document_id, file_type, and location
    """
    chunks: List[Chunk] = []

    for seg_index, segment in enumerate(segments, start=1):
        # ── Requirement 4.6: skip empty/whitespace segments ──────────────────
        if not segment.text or not segment.text.strip():
            logger.warning(
                "Skipping empty/whitespace segment: document_id=%s, segment_index=%d",
                document_id,
                seg_index,
            )
            continue

        # ── Requirement 4.4: whole segment fits in one chunk ─────────────────
        seg_word_count = _word_count(segment.text.strip())
        if seg_word_count <= MAX_WORDS:
            chunks.append(
                _emit_chunk([segment.text.strip()], document_id, file_type, segment.location)
            )
            continue

        # ── Paragraph-level splitting ─────────────────────────────────────────
        paragraphs = _split_by_blank_lines(segment.text)
        buffer: List[str] = []
        buffer_word_count = 0

        for paragraph in paragraphs:
            para_words = _word_count(paragraph)

            if para_words > MAX_WORDS:
                # ── Requirement 4.3: sentence-boundary fallback ───────────────
                sentences = _split_sentences(paragraph)
                for sentence in sentences:
                    sent_words = _word_count(sentence)
                    if buffer_word_count + sent_words > MAX_WORDS:
                        if buffer:
                            chunks.append(
                                _emit_chunk(buffer, document_id, file_type, segment.location)
                            )
                            buffer = _get_overlap_words(buffer)
                            buffer_word_count = _count_words_in_parts(buffer)
                    buffer.append(sentence)
                    buffer_word_count += sent_words
            else:
                # ── Requirement 4.1/4.2: paragraph fits; check capacity ───────
                if buffer_word_count + para_words > MAX_WORDS:
                    if buffer:
                        chunks.append(
                            _emit_chunk(buffer, document_id, file_type, segment.location)
                        )
                        buffer = _get_overlap_words(buffer)
                        buffer_word_count = _count_words_in_parts(buffer)
                buffer.append(paragraph)
                buffer_word_count += para_words

        # flush remaining buffer
        if buffer:
            chunks.append(
                _emit_chunk(buffer, document_id, file_type, segment.location)
            )

    return chunks
