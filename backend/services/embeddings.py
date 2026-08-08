"""
services/embeddings.py — Embedder

Generates vector embeddings for text strings using the Gemini embedding model.

Public API
----------
embed_texts(texts, task_type) -> List[List[float]]
    Calls the Gemini embedding model once per text string (Requirement 5.1).
    Sends requests in small batches with a short delay to respect free-tier
    rate limits (100 requests/minute).
    Reads GEMINI_API_KEY from environment at invocation time (Requirement 5.2).
    Raises GeminiAPIError on any failure (→ HTTP 502).

embed_single(text, task_type) -> List[float]
    Convenience wrapper around embed_texts for a single string.

Requirements: 5.1, 5.2
"""

import logging
import os
import time
from typing import List

import google.generativeai as genai

from services.exceptions import GeminiAPIError

logger = logging.getLogger(__name__)

# Gemini embedding model identifier
_EMBEDDING_MODEL = "models/gemini-embedding-2"

# Free-tier rate limit is 100 requests/minute.
# We send in batches of 80 and wait 65 s between batches to stay well under.
_BATCH_SIZE = 80
_BATCH_DELAY_SECONDS = 65


def embed_texts(
    texts: List[str],
    task_type: str = "retrieval_document",
) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings.

    Calls the Gemini embedding model **once per text** (Requirement 5.1),
    batching requests to respect the free-tier 100 req/min rate limit.

    Parameters
    ----------
    texts     : list of strings to embed (may be empty — returns [])
    task_type : Gemini task type; use "retrieval_document" for chunks and
                "retrieval_query" for questions

    Returns
    -------
    List[List[float]] — one embedding vector per input text, in the same order

    Raises
    ------
    GeminiAPIError
        - If GEMINI_API_KEY is absent or empty (Requirement 5.2)
        - If any individual Gemini API call fails
    """
    # ── Requirement 5.2: check key at invocation time ────────────────────
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiAPIError(
            "GEMINI_API_KEY is not set or empty. "
            "Set the environment variable before calling embed_texts."
        )

    genai.configure(api_key=api_key)

    embeddings: List[List[float]] = []
    total = len(texts)

    for batch_start in range(0, total, _BATCH_SIZE):
        batch = texts[batch_start : batch_start + _BATCH_SIZE]

        # Pause between batches (not before the first one)
        if batch_start > 0:
            logger.info(
                "Embedding rate-limit pause: waiting %ds before next batch "
                "(processed %d/%d texts so far)",
                _BATCH_DELAY_SECONDS,
                batch_start,
                total,
            )
            time.sleep(_BATCH_DELAY_SECONDS)

        for offset, text in enumerate(batch):
            index = batch_start + offset
            try:
                result = genai.embed_content(
                    model=_EMBEDDING_MODEL,
                    content=text,
                    task_type=task_type,
                )
                embeddings.append(result["embedding"])
            except GeminiAPIError:
                raise
            except Exception as exc:
                logger.error(
                    "Gemini embedding failed for text index %d: %s",
                    index,
                    exc,
                )
                raise GeminiAPIError(
                    f"Gemini API error at text index {index}: {exc}"
                ) from exc

    return embeddings


def embed_single(
    text: str,
    task_type: str = "retrieval_document",
) -> List[float]:
    """
    Generate an embedding for a single text string.

    Convenience wrapper around embed_texts.

    Parameters
    ----------
    text      : the string to embed
    task_type : Gemini task type (default: "retrieval_document")

    Returns
    -------
    List[float] — embedding vector for the input text

    Raises
    ------
    GeminiAPIError
        - If GEMINI_API_KEY is absent or empty
        - If the Gemini API call fails
    """
    results = embed_texts([text], task_type=task_type)
    return results[0]
