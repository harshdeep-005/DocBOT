"""
Property 4: Magic-Bytes-First Type Detection
=============================================

**Validates: Requirement 2.1**

These property-based tests verify that the router's `_detect_type` function
always prioritises magic bytes over the declared MIME type and filename
extension when determining the file type.

Four properties are tested:
  1. PDF magic bytes (`%PDF`) override any non-PDF MIME type / extension.
  2. DOCX magic bytes (ZIP + word/ entries) override any non-DOCX MIME / extension.
  3. PPTX magic bytes (ZIP + ppt/ entries) override any non-PPTX MIME / extension.
  4. When magic bytes are inconclusive the MIME type is used as a fallback.
"""

import io
import sys
import os
import zipfile

# ---------------------------------------------------------------------------
# Path setup — tests are run from backend/ so the package root is already on
# the path when invoked via `python -m pytest`.  Adding it explicitly makes
# the file runnable from any working directory as well.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_BACKEND_DIR))

from hypothesis import given, settings
import hypothesis.strategies as st

from services.extraction.router import _detect_type


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _make_zip(entries: dict) -> bytes:
    """Build a minimal in-memory ZIP with the given filename→content mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _make_docx_bytes() -> bytes:
    """Return bytes for a minimal valid DOCX ZIP archive."""
    return _make_zip({
        "[Content_Types].xml": b"<Types/>",
        "word/document.xml": b"<document/>",
    })


def _make_pptx_bytes() -> bytes:
    """Return bytes for a minimal valid PPTX ZIP archive."""
    return _make_zip({
        "[Content_Types].xml": b"<Types/>",
        "ppt/presentation.xml": b"<presentation/>",
    })


# ---------------------------------------------------------------------------
# Non-PDF MIME types and filenames used as misleading metadata
# ---------------------------------------------------------------------------

_NON_PDF_MIMES = st.sampled_from([
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "application/octet-stream",
])

_NON_PDF_FILENAMES = st.sampled_from([
    "file.docx",
    "file.pptx",
    "file.txt",
    "file.md",
    "file.bin",
])

_NON_DOCX_MIMES = st.sampled_from([
    "application/pdf",
    "text/plain",
])

_NON_DOCX_FILENAMES = st.sampled_from([
    "file.pdf",
    "file.txt",
])

_NON_PPTX_MIMES = st.sampled_from([
    "application/pdf",
    "text/plain",
])

_NON_PPTX_FILENAMES = st.sampled_from([
    "file.pdf",
    "file.txt",
])


# ---------------------------------------------------------------------------
# Test 1 — PDF magic bytes override non-PDF MIME and extension
# ---------------------------------------------------------------------------

@given(
    suffix=st.binary(min_size=0, max_size=100),
    mime_type=_NON_PDF_MIMES,
    filename=_NON_PDF_FILENAMES,
)
@settings(max_examples=100)
def test_pdf_magic_overrides_mime_and_extension(suffix, mime_type, filename):
    """
    **Validates: Requirement 2.1**

    Whenever the first 4 bytes are b"%PDF", `_detect_type` must return "pdf"
    regardless of the MIME type or filename extension supplied by the client.
    """
    file_bytes = b"%PDF" + suffix
    result = _detect_type(file_bytes, filename, mime_type)
    assert result == "pdf", (
        f"Expected 'pdf' for PDF magic bytes but got {result!r} "
        f"(mime={mime_type!r}, filename={filename!r})"
    )


# ---------------------------------------------------------------------------
# Test 2 — DOCX magic bytes (ZIP + word/) override non-DOCX MIME and extension
# ---------------------------------------------------------------------------

@given(
    mime_type=_NON_DOCX_MIMES,
    filename=_NON_DOCX_FILENAMES,
)
@settings(max_examples=20)
def test_docx_magic_overrides_mime_and_extension(mime_type, filename):
    """
    **Validates: Requirement 2.1**

    A ZIP archive containing [Content_Types].xml and a word/ entry must be
    detected as "docx" regardless of the declared MIME type or filename.
    """
    file_bytes = _make_docx_bytes()
    result = _detect_type(file_bytes, filename, mime_type)
    assert result == "docx", (
        f"Expected 'docx' for DOCX ZIP bytes but got {result!r} "
        f"(mime={mime_type!r}, filename={filename!r})"
    )


# ---------------------------------------------------------------------------
# Test 3 — PPTX magic bytes (ZIP + ppt/) override non-PPTX MIME and extension
# ---------------------------------------------------------------------------

@given(
    mime_type=_NON_PPTX_MIMES,
    filename=_NON_PPTX_FILENAMES,
)
@settings(max_examples=20)
def test_pptx_magic_overrides_mime_and_extension(mime_type, filename):
    """
    **Validates: Requirement 2.1**

    A ZIP archive containing [Content_Types].xml and a ppt/ entry must be
    detected as "pptx" regardless of the declared MIME type or filename.
    """
    file_bytes = _make_pptx_bytes()
    result = _detect_type(file_bytes, filename, mime_type)
    assert result == "pptx", (
        f"Expected 'pptx' for PPTX ZIP bytes but got {result!r} "
        f"(mime={mime_type!r}, filename={filename!r})"
    )


# ---------------------------------------------------------------------------
# Test 4 — MIME fallback is used when magic bytes are inconclusive
# ---------------------------------------------------------------------------

_NON_MAGIC_BYTES = st.binary(min_size=4, max_size=200).filter(
    lambda b: not b.startswith(b"%PDF") and not b.startswith(b"PK\x03\x04")
)


@given(file_bytes=_NON_MAGIC_BYTES)
@settings(max_examples=100)
def test_mime_fallback_txt(file_bytes):
    """
    **Validates: Requirement 2.1**

    When magic bytes are neither PDF nor ZIP, text/plain MIME + .txt extension
    must yield "txt".
    """
    result = _detect_type(file_bytes, "file.txt", "text/plain")
    assert result == "txt", (
        f"Expected 'txt' for text/plain + .txt filename but got {result!r}"
    )


@given(file_bytes=_NON_MAGIC_BYTES)
@settings(max_examples=100)
def test_mime_fallback_md(file_bytes):
    """
    **Validates: Requirement 2.1**

    When magic bytes are neither PDF nor ZIP, text/plain MIME + .md extension
    must yield "md".
    """
    result = _detect_type(file_bytes, "file.md", "text/plain")
    assert result == "md", (
        f"Expected 'md' for text/plain + .md filename but got {result!r}"
    )


@given(file_bytes=_NON_MAGIC_BYTES)
@settings(max_examples=100)
def test_mime_fallback_pdf_mime(file_bytes):
    """
    **Validates: Requirement 2.1**

    When magic bytes are inconclusive but MIME is application/pdf the router
    must fall back to "pdf" via the MIME branch.
    """
    result = _detect_type(file_bytes, "file.bin", "application/pdf")
    assert result == "pdf", (
        f"Expected 'pdf' for application/pdf MIME fallback but got {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Unsupported type raises UnsupportedTypeError with informative message
# ---------------------------------------------------------------------------

_SUPPORTED_MIMES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
}

# Byte sequences that do NOT start with PDF magic or ZIP magic.
# Must be at least 4 bytes so _read_magic doesn't raise UnreadableFileError.
_NON_MAGIC_NON_SUPPORTED = st.binary(min_size=4, max_size=200).filter(
    lambda b: not b.startswith(b"%PDF") and not b.startswith(b"PK\x03\x04")
)

# MIME types that are not in the supported set.
# We generate arbitrary printable text strings and filter out supported ones.
_UNSUPPORTED_MIMES = st.from_regex(
    r"[a-z]+/[a-z0-9.\-+]+", fullmatch=True
).filter(lambda m: m not in _SUPPORTED_MIMES)


@given(
    file_bytes=_NON_MAGIC_NON_SUPPORTED,
    mime_type=_UNSUPPORTED_MIMES,
    filename=st.sampled_from(["file.bin", "file.xyz", "file.dat", "file.unknown"]),
)
@settings(max_examples=100)
def test_unsupported_type_raises_415_error(file_bytes, mime_type, filename):
    """
    **Validates: Requirements 2.6**

    When the file has no recognised magic bytes AND the declared MIME type is
    not one of the supported types, `_detect_type` must raise
    `UnsupportedTypeError`.  The `.message` attribute must:
      - contain the detected type string (the normalised MIME), and
      - contain the substring "Accepted:" (confirming the list of accepted
        types is included in the error message).
    """
    from services.extraction.router import UnsupportedTypeError

    try:
        _detect_type(file_bytes, filename, mime_type)
        assert False, (
            f"Expected UnsupportedTypeError but _detect_type returned normally "
            f"(mime={mime_type!r}, filename={filename!r})"
        )
    except UnsupportedTypeError as exc:
        detected = mime_type.strip().lower()
        assert detected in exc.message, (
            f"Expected detected type {detected!r} to appear in error message, "
            f"but got: {exc.message!r}"
        )
        assert "Accepted:" in exc.message, (
            f"Expected 'Accepted:' in error message, but got: {exc.message!r}"
        )
