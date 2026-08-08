"""
services/generation.py — Generator

Builds a grounded prompt and calls the Gemini LLM to generate an answer
that is based exclusively on the retrieved context chunks.

Public API
----------
build_prompt(question, chunks) -> str
    Constructs the grounded prompt from the question and chunk texts.

generate_answer(question, chunks) -> str
    Calls the Gemini LLM with the constructed prompt and returns the answer.
    Raises GeminiAPIError on any failure (→ HTTP 502).

Requirements: 6.5, 6.7
"""

import logging
import os
from typing import List

import google.generativeai as genai

from models.schemas import Chunk
from services.exceptions import GeminiAPIError

logger = logging.getLogger(__name__)

# Gemini generative model identifier
_GENERATIVE_MODEL = "gemini-3.6-flash"

# The exact "not found" phrase the LLM is instructed to use and that the
# route layer checks for (Requirement 6.7).
NOT_FOUND_PHRASE = "The answer was not found in the uploaded document."

# Prompt template — the phrasing here is part of the spec contract
_PROMPT_TEMPLATE = (
    "You are a document Q&A assistant. Answer the user's question using ONLY\n"
    "the context passages provided below. Do not use any external knowledge.\n"
    "\n"
    "If the answer cannot be found in the provided context, respond with exactly:\n"
    '"{not_found_phrase}"\n'
    "\n"
    "Context:\n"
    "{context_block}"
    "\n"
    "Question: {question}\n"
    "\n"
    "Answer:"
)


def build_prompt(question: str, chunks: List[Chunk]) -> str:
    """
    Construct a grounded prompt that instructs the LLM to answer only from
    the supplied context and to use the fixed "not found" phrase when the
    answer is absent (Requirement 6.5).

    Parameters
    ----------
    question : the user's natural-language question
    chunks   : the retrieved context chunks whose texts are embedded

    Returns
    -------
    str — the fully-formatted prompt ready to pass to the LLM
    """
    # Build the context block: each chunk text is wrapped by --- separators
    context_parts: List[str] = []
    for chunk in chunks:
        context_parts.append(f"---\n{chunk.text}")
    # Append a final separator after the last chunk
    context_parts.append("---\n")

    context_block = "\n".join(context_parts)

    return _PROMPT_TEMPLATE.format(
        not_found_phrase=NOT_FOUND_PHRASE,
        context_block=context_block,
        question=question,
    )


def generate_answer(question: str, chunks: List[Chunk]) -> str:
    """
    Call the Gemini LLM with a grounded prompt built from the question and
    retrieved chunks. Returns the raw answer text from the model.

    The route layer is responsible for mapping the NOT_FOUND_PHRASE response
    to the appropriate HTTP 200 answer field (Requirement 6.7).

    Parameters
    ----------
    question : the user's natural-language question
    chunks   : the retrieved context chunks

    Returns
    -------
    str — the answer text produced by the LLM

    Raises
    ------
    GeminiAPIError
        - If GEMINI_API_KEY is absent or empty (Requirement 5.2 / 9.1)
        - If the Gemini generative API call fails for any reason
    """
    # Check key at invocation time (Requirement 5.2 / 9.1)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiAPIError(
            "GEMINI_API_KEY is not set or empty. "
            "Set the environment variable before calling generate_answer."
        )

    genai.configure(api_key=api_key)

    prompt = build_prompt(question, chunks)

    try:
        model = genai.GenerativeModel(_GENERATIVE_MODEL)
        response = model.generate_content(prompt)
        return response.text
    except GeminiAPIError:
        # Re-raise our own errors without double-wrapping
        raise
    except Exception as exc:
        logger.error("Gemini generation failed: %s", exc)
        raise GeminiAPIError(
            f"Gemini generation API call failed: {exc}"
        ) from exc
