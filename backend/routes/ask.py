"""
routes/ask.py — POST /ask

Orchestrates the full RAG query pipeline:
  1. Validate question length (1–2000 chars) → HTTP 422 if invalid
  2. Embed question with Gemini (task_type="retrieval_query") → HTTP 502 on failure
  3. Similarity search in Chroma scoped to document_id (top-k = TOP_K_CHUNKS)
  4. If no chunks found → return "not found" phrase with HTTP 200
  5. Build grounded prompt and call Gemini LLM → HTTP 502 on failure
  6. If LLM response contains "not found" phrase → return fixed phrase
  7. Build deduplicated, sorted citations list
  8. Return HTTP 200 { answer, citations, chunks }

Requirements: 6.2–6.8, 7.1
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from config import get_top_k_chunks
from models.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    FileType,
    SourceChunk,
)
from services.embeddings import embed_single
from services.exceptions import GeminiAPIError
from services.generation import NOT_FOUND_PHRASE, generate_answer
from services.vector_store import similarity_search

logger = logging.getLogger(__name__)

router = APIRouter()

# ── File types that produce "Page N" citations ────────────────────────────────
_PAGE_TYPES = {FileType.PDF, FileType.DOCX}
# ── File types that produce "Slide N" citations ───────────────────────────────
_SLIDE_TYPES = {FileType.PPTX}


@router.post("/", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """
    RAG query endpoint.

    Validates the question, embeds it, retrieves relevant chunks, generates
    a grounded answer, and returns citations alongside the source chunks.

    Returns
    -------
    AskResponse
        { answer, citations, chunks } on success (HTTP 200)

    Raises
    ------
    HTTPException 422
        When the question is empty or exceeds 2000 characters.
    HTTPException 502
        When the Gemini embedding or LLM API call fails.
    """
    question = request.question
    document_id = request.document_id

    # ── Step 1: Manual validation guard (Requirement 6.9) ────────────────────
    # Pydantic's min_length/max_length on AskRequest already triggers a 422,
    # but this explicit guard ensures the exact error message specified in the
    # design is returned.
    if not question or len(question) > 2000:
        raise HTTPException(
            status_code=422,
            detail="Question must be between 1 and 2000 characters",
        )

    top_k = get_top_k_chunks()

    logger.info(
        "POST /ask: document_id=%r question_len=%d top_k=%d",
        document_id,
        len(question),
        top_k,
    )

    # ── Step 2: Embed question (Requirement 6.3) ──────────────────────────────
    try:
        query_embedding: List[float] = embed_single(
            question, task_type="retrieval_query"
        )
    except GeminiAPIError as exc:
        api_reason = str(exc)
        logger.error("Embedding API call failed for /ask: %s", api_reason)
        raise HTTPException(
            status_code=502,
            detail=f"embed API call failed: {api_reason}",
        )

    # ── Step 3: Similarity search (Requirement 6.4) ───────────────────────────
    from models.schemas import Chunk  # local import to avoid circular at top
    chunks: List[Chunk] = similarity_search(document_id, query_embedding, top_k)

    # ── Step 4: No chunks found → "not found" response (Requirement 6.7) ─────
    if not chunks:
        logger.info(
            "No chunks found for document_id=%r — returning not-found phrase",
            document_id,
        )
        return AskResponse(
            answer=NOT_FOUND_PHRASE,
            citations=[],
            chunks=[],
        )

    # ── Step 5: Generate answer (Requirement 6.5) ─────────────────────────────
    try:
        answer: str = generate_answer(question, chunks)
    except GeminiAPIError as exc:
        api_reason = str(exc)
        logger.error("Generation API call failed for /ask: %s", api_reason)
        raise HTTPException(
            status_code=502,
            detail=f"generation API call failed: {api_reason}",
        )

    # ── Step 6: Check for "not found" phrase in LLM response (Req. 6.7) ──────
    if NOT_FOUND_PHRASE in answer:
        answer = NOT_FOUND_PHRASE

    # ── Step 7: Build deduplicated, sorted citations (Requirement 7.1) ────────
    # Dedup key = location integer; format "Page N" for PDF/DOCX, "Slide N"
    # for PPTX; TXT/MD chunks have no location → produce no citation.
    seen_locations: dict[int, Citation] = {}
    for chunk in chunks:
        if chunk.location is None:
            continue  # TXT/MD — no citation
        if chunk.location in seen_locations:
            continue  # already have a citation for this location

        if chunk.file_type in _PAGE_TYPES:
            label = f"Page {chunk.location}"
        elif chunk.file_type in _SLIDE_TYPES:
            label = f"Slide {chunk.location}"
        else:
            continue  # unsupported type — skip

        seen_locations[chunk.location] = Citation(
            label=label,
            location=chunk.location,
        )

    citations: List[Citation] = sorted(
        seen_locations.values(), key=lambda c: c.location
    )

    # ── Step 8: Build SourceChunk list (1-based rank) ─────────────────────────
    source_chunks: List[SourceChunk] = []
    for rank, chunk in enumerate(chunks, start=1):
        chunk_citation: Optional[Citation] = (
            seen_locations.get(chunk.location)
            if chunk.location is not None
            else None
        )
        source_chunks.append(
            SourceChunk(
                rank=rank,
                text=chunk.text,
                citation=chunk_citation,
            )
        )

    logger.info(
        "POST /ask completed: document_id=%r chunks=%d citations=%d",
        document_id,
        len(source_chunks),
        len(citations),
    )

    # ── Step 9: Return success response (Requirement 6.6) ─────────────────────
    return AskResponse(
        answer=answer,
        citations=citations,
        chunks=source_chunks,
    )
