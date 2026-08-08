"""
services/extraction/router.py — File-type detection and extractor routing.

Detection order (Requirement 2.1):
  1. Inspect magic bytes (first 8 bytes of the file).
  2. Fall back to the declared MIME type when magic bytes are inconclusive.
  3. Use the .md file extension as a tiebreaker when MIME type is text/plain.

Supported formats and their magic byte signatures:
  PDF   — 25 50 44 46  ("%PDF")
  DOCX  — 50 4B 03 04  (ZIP) + "[Content_Types].xml" + "word/" entry
  PPTX  — 50 4B 03 04  (ZIP) + "[Content_Types].xml" + "ppt/" entry

TXT / MD carry no magic bytes and are resolved via MIME + extension.

Errors:
  UnsupportedTypeError  — raised when the detected type is not supported
                          (→ HTTP 415 in the upload route)
  UnreadableFileError   — raised when the file header cannot be read or the
                          ZIP structure is corrupt (→ HTTP 422 in the upload
                          route)
"""

from __future__ import annotations

import io
import logging
import os
import zipfile
from typing import List

from models.schemas import TextSegment

from .docx import extract_docx
from .pdf import extract_pdf
from .plain_text import extract_plain_text
from .pptx import extract_pptx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Magic byte constants
# ---------------------------------------------------------------------------
_PDF_MAGIC = b"%PDF"          # 25 50 44 46
_ZIP_MAGIC = b"PK\x03\x04"   # 50 4B 03 04

# Accepted type names used in error messages
_ACCEPTED_TYPES = "pdf, docx, pptx, txt, md"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class UnsupportedTypeError(Exception):
    """
    Raised when the detected file type is not one of the supported formats.
    The upload route maps this to HTTP 415.

    Attributes:
        detected_type: Human-readable string describing the detected type.
        message: Full error message ready for the HTTP response body.
    """

    def __init__(self, detected_type: str) -> None:
        self.detected_type = detected_type
        self.message = (
            f"Unsupported type '{detected_type}'. "
            f"Accepted: {_ACCEPTED_TYPES}"
        )
        super().__init__(self.message)


class UnreadableFileError(Exception):
    """
    Raised when the file header cannot be inspected (corrupt or empty file).
    The upload route maps this to HTTP 422.

    Attributes:
        message: Full error message ready for the HTTP response body.
    """

    def __init__(self, detail: str = "unreadable header") -> None:
        self.message = f"File could not be read: {detail}"
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_magic(file_bytes: bytes) -> bytes:
    """Return the first 8 bytes; raise UnreadableFileError if the file is
    shorter than 4 bytes (minimum needed for any magic sequence)."""
    if len(file_bytes) < 4:
        raise UnreadableFileError("file is too short to determine type")
    return file_bytes[:8]


def _classify_zip(file_bytes: bytes) -> str:
    """
    Open the ZIP archive contained in *file_bytes* and inspect its entry
    names to distinguish DOCX from PPTX.

    Returns 'docx', 'pptx', or raises UnsupportedTypeError / UnreadableFileError.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile as exc:
        raise UnreadableFileError("ZIP archive is corrupt or truncated") from exc
    except Exception as exc:
        raise UnreadableFileError(f"could not open ZIP archive: {exc}") from exc

    has_content_types = "[Content_Types].xml" in names
    has_word = any(n.startswith("word/") for n in names)
    has_ppt = any(n.startswith("ppt/") for n in names)

    if has_content_types and has_word:
        return "docx"
    if has_content_types and has_ppt:
        return "pptx"

    # ZIP file that is neither DOCX nor PPTX
    raise UnsupportedTypeError("zip (unknown Office format)")


def _detect_type(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """
    Determine the canonical file type string ('pdf', 'docx', 'pptx', 'txt',
    or 'md') for the given file.

    Detection order:
      1. Magic bytes → definitive for PDF and ZIP-based formats.
      2. Declared MIME type → used when magic bytes are inconclusive.
      3. File extension → used only as a tiebreaker between 'txt' and 'md'
         when MIME type is 'text/plain'.

    Raises:
        UnreadableFileError: When magic bytes cannot be read.
        UnsupportedTypeError: When the type cannot be matched to any
                              supported format.
    """
    magic = _read_magic(file_bytes)  # may raise UnreadableFileError

    # --- Magic-bytes detection -------------------------------------------
    if magic[:4] == _PDF_MAGIC:
        return "pdf"

    if magic[:4] == _ZIP_MAGIC:
        # DOCX and PPTX are both ZIP archives; inspect the entry list.
        return _classify_zip(file_bytes)  # returns 'docx' or 'pptx'

    # --- MIME-type fallback ----------------------------------------------
    norm_mime = (mime_type or "").strip().lower()

    if norm_mime == "application/pdf":
        return "pdf"

    if norm_mime in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return "docx"

    if norm_mime in (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    ):
        return "pptx"

    if norm_mime == "text/plain":
        # Tiebreaker: use the file extension to distinguish MD from TXT.
        ext = os.path.splitext(filename or "")[1].lower()
        return "md" if ext == ".md" else "txt"

    if norm_mime in ("text/markdown", "text/x-markdown"):
        return "md"

    # --- No match --------------------------------------------------------
    detected = norm_mime if norm_mime else "unknown"
    raise UnsupportedTypeError(detected)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_and_route(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> List[TextSegment]:
    """
    Detect the file type of *file_bytes* and delegate to the appropriate
    extractor.

    Detection uses magic bytes first, falls back to *mime_type*, and uses
    the *.md* extension as a tiebreaker when MIME type is ``text/plain``.

    Args:
        file_bytes: Complete raw bytes of the uploaded file.
        filename:   Original filename (used for the .md extension check).
        mime_type:  MIME type declared by the HTTP client.

    Returns:
        List[TextSegment] produced by the matched extractor.

    Raises:
        UnsupportedTypeError: The detected type is not supported (→ HTTP 415).
        UnreadableFileError:  The file header cannot be read (→ HTTP 422).
    """
    file_type = _detect_type(file_bytes, filename, mime_type)

    logger.debug(
        "detect_and_route: filename=%r mime_type=%r → detected type=%r",
        filename,
        mime_type,
        file_type,
    )

    if file_type == "pdf":
        return extract_pdf(file_bytes)
    if file_type == "docx":
        return extract_docx(file_bytes)
    if file_type == "pptx":
        return extract_pptx(file_bytes)
    if file_type in ("txt", "md"):
        return extract_plain_text(file_bytes)

    # Defensive: _detect_type should always return a known type or raise, but
    # guard against future changes.
    raise UnsupportedTypeError(file_type)
