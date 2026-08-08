"""
Unit tests for file-type detection in services/extraction/router.py

Task 3.4 — one representative test per supported type plus error-path tests.

Validates: Requirements 1.4, 2.1–2.7
"""

import io
import sys
import os
import zipfile

# ---------------------------------------------------------------------------
# Path setup — makes the file runnable from any working directory
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_BACKEND_DIR))

import pytest

from services.extraction.router import (
    _detect_type,
    UnsupportedTypeError,
    UnreadableFileError,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_zip(entries: dict) -> bytes:
    """Build a minimal in-memory ZIP with the given filename→content mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests 1–5: one representative test per supported type
# ---------------------------------------------------------------------------

def test_detect_pdf():
    """PDF magic bytes + matching MIME/extension → 'pdf'."""
    file_bytes = b"%PDF-1.4 test"
    result = _detect_type(file_bytes, "document.pdf", "application/pdf")
    assert result == "pdf"


def test_detect_docx():
    """DOCX ZIP structure + matching MIME/extension → 'docx'."""
    file_bytes = _make_zip({
        "[Content_Types].xml": b"<Types/>",
        "word/document.xml": b"<doc/>",
    })
    result = _detect_type(
        file_bytes,
        "file.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert result == "docx"


def test_detect_pptx():
    """PPTX ZIP structure + matching MIME/extension → 'pptx'."""
    file_bytes = _make_zip({
        "[Content_Types].xml": b"<Types/>",
        "ppt/presentation.xml": b"<prs/>",
    })
    result = _detect_type(
        file_bytes,
        "file.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    assert result == "pptx"


def test_detect_txt():
    """Non-magic bytes + text/plain MIME + .txt extension → 'txt'."""
    file_bytes = b"\x00\x01\x02\x03"
    result = _detect_type(file_bytes, "file.txt", "text/plain")
    assert result == "txt"


def test_detect_md():
    """Non-magic bytes + text/plain MIME + .md extension → 'md'."""
    file_bytes = b"\x00\x01\x02\x03"
    result = _detect_type(file_bytes, "file.md", "text/plain")
    assert result == "md"


# ---------------------------------------------------------------------------
# Test 6: corrupt / too-short header → UnreadableFileError (HTTP 422)
# ---------------------------------------------------------------------------

def test_corrupt_header_raises_unreadable():
    """File shorter than 4 bytes raises UnreadableFileError containing 'could not be read'."""
    with pytest.raises(UnreadableFileError) as exc_info:
        _detect_type(b"\x00", "file.pdf", "application/pdf")

    assert "could not be read" in exc_info.value.message


# ---------------------------------------------------------------------------
# Test 7: unsupported type + file > 50 MB → UnsupportedTypeError (HTTP 415),
#          NOT a size-related error; confirms type is evaluated first
# ---------------------------------------------------------------------------

def test_unsupported_type_large_file_raises_415_not_size():
    """Unsupported MIME on a >50 MB file raises UnsupportedTypeError, not a size error."""
    file_bytes = b"\xDE\xAD\xBE\xEF" + b"\x00" * (51 * 1024 * 1024)
    with pytest.raises(UnsupportedTypeError):
        _detect_type(file_bytes, "file.bin", "application/x-custom")
