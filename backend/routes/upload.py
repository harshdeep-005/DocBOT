"""
routes/upload.py — POST /upload

Orchestrates the full document ingestion pipeline:
  1. Read file bytes
  2. Detect file type (HTTP 415 / HTTP 422 on failure)
  3. Validate size ≤ 50 MB (HTTP 422)
  4. Validate page/slide count ≤ 300 (HTTP 422) for PDF and PPTX
  5. Generate UUID4 document_id
  6. Extract text segments
  7. Chunk segments
  8. Embed chunks (HTTP 502 on failure + rollback)
  9. Store in vector store (HTTP 500 on failure + rollback)
 10. Return HTTP 200 { document_id, chunk_count }

Requirements: 1.3, 1.4, 1.5, 3.6, 5.5, 5.6, 5.7
"""

import io
import logging
import re
import uuid
from typing import List

import fitz  # PyMuPDF
from fastapi import APIRouter, File, HTTPException, UploadFile
from pptx import Presentation

from models.schemas import Chunk, FileType, UploadResponse
from services.chunking import chunk_segments
from services.embeddings import embed_texts
from services.exceptions import GeminiAPIError, VectorStoreError
from services.extraction.router import (
    UnreadableFileError,
    UnsupportedTypeError,
    _detect_type,
    detect_and_route,
)
from services.vector_store import replace_document_chunks, rollback_document

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Constants ──────────────────────────────────────────────────────────────────

_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
_MAX_PAGES = 300

# Map detected type string → FileType enum
_FILE_TYPE_MAP = {
    "pdf": FileType.PDF,
    "docx": FileType.DOCX,
    "pptx": FileType.PPTX,
    "txt": FileType.TXT,
    "md": FileType.MD,
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _count_pages(file_bytes: bytes, detected_type: str) -> int:
    """
    Count pages/slides for PDF and PPTX.
    Returns 0 for DOCX, TXT, MD (no page count check needed).
    """
    if detected_type == "pdf":
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            count = len(doc)
            doc.close()
            return count
        except Exception as exc:
            logger.warning("Could not count PDF pages: %s", exc)
            return 0  # if we can't count, skip the limit check
    elif detected_type == "pptx":
        try:
            prs = Presentation(io.BytesIO(file_bytes))
            return len(prs.slides)
        except Exception as exc:
            logger.warning("Could not count PPTX slides: %s", exc)
            return 0
    return 0  # DOCX, TXT, MD — no page count validation


# ── Route handler ──────────────────────────────────────────────────────────────

@router.post("/", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """
    Validates, extracts, chunks, embeds, and stores an uploaded document.
    Returns UploadResponse on success; raises HTTPException on failure.

    Processing order (Requirements 1.4, 1.5):
      1. Read file bytes
      2. Detect file type FIRST → HTTP 415 / 422 before checking size
      3. Validate size ≤ 50 MB → HTTP 422
      4. Validate page/slide count ≤ 300 → HTTP 422
      5. Generate document_id, extract, chunk, embed, store
    """
    filename = file.filename or ""

    # ── Step 1: Read file bytes ───────────────────────────────────────────────
    try:
        file_bytes = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded file %r: %s", filename, exc)
        raise HTTPException(status_code=422, detail="File could not be read: unreadable header")

    mime_type = file.content_type or ""

    # ── Step 2: Detect file type FIRST (Requirement 1.4) ─────────────────────
    # Return HTTP 415 for unsupported type, HTTP 422 for unreadable header
    # — both BEFORE evaluating the size limit.
    try:
        detected_type = _detect_type(file_bytes, filename, mime_type)
    except UnsupportedTypeError as exc:
        raise HTTPException(status_code=415, detail=exc.message)
    except UnreadableFileError as exc:
        raise HTTPException(status_code=422, detail=exc.message)

    # ── Step 3: Validate file size ≤ 50 MB (Requirement 1.5) ─────────────────
    if len(file_bytes) > _MAX_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="File exceeds the 50 MB size limit")

    # ── Step 4: Validate page/slide count ≤ 300 (Requirement 1.5) ────────────
    # Only applies to PDF and PPTX; DOCX page count is not reliably accessible.
    page_count = _count_pages(file_bytes, detected_type)
    if page_count > _MAX_PAGES:
        raise HTTPException(
            status_code=422,
            detail="Document exceeds the 300 page/slide limit",
        )

    # ── Step 5: Generate document_id ─────────────────────────────────────────
    document_id = str(uuid.uuid4())
    file_type = _FILE_TYPE_MAP[detected_type]

    logger.info(
        "Starting ingestion: document_id=%r filename=%r type=%r size=%d bytes",
        document_id,
        filename,
        detected_type,
        len(file_bytes),
    )

    # ── Step 6: Extract text segments (Requirement 3.6) ──────────────────────
    try:
        segments = detect_and_route(file_bytes, filename, mime_type)
    except UnsupportedTypeError as exc:
        # Defensive: should not reach here after step 2, but guard anyway
        raise HTTPException(status_code=415, detail=exc.message)
    except UnreadableFileError as exc:
        raise HTTPException(status_code=422, detail=exc.message)
    except Exception as exc:
        exc_type = type(exc).__name__
        logger.error("Extraction failed for %r: %s", filename, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed for '{filename}': {exc_type}",
        )

    # ── Step 7: Chunk segments ────────────────────────────────────────────────
    chunks: List[Chunk] = chunk_segments(segments, document_id, file_type)

    logger.info(
        "Chunking complete: document_id=%r chunk_count=%d",
        document_id,
        len(chunks),
    )

    # ── Step 8: Embed chunks (Requirement 5.5) ────────────────────────────────
    texts = [chunk.text for chunk in chunks]
    try:
        embeddings = embed_texts(texts, task_type="retrieval_document")
    except GeminiAPIError as exc:
        # Determine which chunk index failed from the exception message if possible
        api_reason = str(exc)
        logger.error(
            "Embedding failed for document_id=%r: %s — rolling back",
            document_id,
            api_reason,
        )
        rollback_document(document_id)  # best-effort; never raises
        # Try to extract the chunk index from the error message
        # GeminiAPIError message format: "Gemini API error at text index {i}: ..."
        chunk_index = 0
        m = re.search(r"text index (\d+)", api_reason)
        if m:
            chunk_index = int(m.group(1))
        raise HTTPException(
            status_code=502,
            detail=f"Embedding failed at chunk index {chunk_index}: {api_reason}",
        )

    # ── Step 9: Store in vector store (Requirement 5.7) ──────────────────────
    try:
        replace_document_chunks(document_id, chunks, embeddings)
    except VectorStoreError as exc:
        message = str(exc)
        logger.error(
            "Vector store write failed for document_id=%r: %s — rolling back",
            document_id,
            message,
        )
        rollback_document(document_id)  # best-effort; never raises
        raise HTTPException(status_code=500, detail=message)

    chunk_count = len(chunks)
    logger.info(
        "Ingestion complete: document_id=%r chunk_count=%d",
        document_id,
        chunk_count,
    )

    # ── Step 10: Return success (Requirement 5.6) ─────────────────────────────
    return UploadResponse(document_id=document_id, chunk_count=chunk_count)
