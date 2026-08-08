"""
Unit tests for services/chunking.py

Requirements: 4.3, 4.4, 4.6
"""

import logging

import pytest

from models.schemas import FileType, TextSegment
from services.chunking import chunk_segments


# ── helpers ───────────────────────────────────────────────────────────────────

def _word_count(text: str) -> int:
    return len(text.split())


def _make_words(n: int, word: str = "word") -> str:
    """Return a string containing exactly *n* copies of *word*."""
    return " ".join([word] * n)


def _make_paragraph(n_words: int, word: str = "word") -> str:
    return _make_words(n_words, word)


# ── Test 1: Short segment → exactly one chunk (Requirement 4.4) ──────────────

def test_short_segment_produces_single_chunk():
    """
    A TextSegment whose text is fewer than 500 words must be returned as
    exactly one chunk containing the full text.
    """
    text = _make_words(50)
    segment = TextSegment(text=text)
    chunks = chunk_segments([segment], document_id="doc-1", file_type=FileType.TXT)

    assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
    assert _word_count(chunks[0].text) == 50


# ── Test 2: Empty segment → warning + skip; valid segment still chunked ───────

def test_empty_segment_logs_warning_and_is_skipped(caplog):
    """
    An empty/whitespace segment must:
      - log a WARNING containing the document_id and the 1-based index (1)
      - emit no chunk for that segment
    The following valid segment must still produce exactly one chunk.
    """
    empty_segment = TextSegment(text="   ")
    valid_segment = TextSegment(text=_make_words(30))

    with caplog.at_level(logging.WARNING, logger="services.chunking"):
        chunks = chunk_segments(
            [empty_segment, valid_segment],
            document_id="doc-warn-test",
            file_type=FileType.PDF,
        )

    # Only the valid segment should produce a chunk
    assert len(chunks) == 1, f"Expected 1 chunk (from valid segment), got {len(chunks)}"

    # Warning must mention document_id and segment index 1
    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("doc-warn-test" in msg for msg in warning_messages), (
        "Warning must contain the document_id. Got: " + str(warning_messages)
    )
    assert any("1" in msg for msg in warning_messages), (
        "Warning must contain the 1-based segment index (1). Got: " + str(warning_messages)
    )


# ── Test 3: Oversized single paragraph → sentence split, all ≤ 500 words ─────

def test_oversized_paragraph_is_split_at_sentence_boundary():
    """
    A segment whose entire text is one paragraph (no blank lines) of ~600 words
    must be split so that every chunk has ≤ 500 words.
    """
    # Build ~600-word single paragraph: 12 sentences of ~50 words each
    sentence = _make_words(50) + "."
    single_paragraph = " ".join([sentence] * 12)  # 600 words (no blank lines)

    segment = TextSegment(text=single_paragraph)
    chunks = chunk_segments([segment], document_id="doc-big-para", file_type=FileType.TXT)

    assert len(chunks) >= 2, "Expected at least 2 chunks for ~600-word paragraph"
    for i, chunk in enumerate(chunks):
        wc = _word_count(chunk.text)
        assert wc <= 500, (
            f"Chunk {i} exceeds 500 words: {wc} words."
        )
