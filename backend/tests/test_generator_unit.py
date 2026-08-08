"""
tests/test_generator_unit.py — Unit tests for the Generator

Tests for generate_answer in services/generation.py:
  1. When the LLM returns the "not found" phrase, generate_answer returns it as-is.
  2. When the Gemini API raises an exception, generate_answer raises GeminiAPIError.
"""

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

from models.schemas import Chunk, FileType
from services.exceptions import GeminiAPIError
from services.generation import NOT_FOUND_PHRASE, generate_answer

# ── Helpers ──────────────────────────────────────────────────────────────────

def make_chunk(text: str = "Some context text.") -> Chunk:
    """Create a minimal Chunk for testing."""
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id="doc-test-001",
        file_type=FileType.PDF,
        text=text,
        location=1,
    )


# ── Tests ────────────────────────────────────────────────────────────────────

class TestGenerateAnswerNotFoundPhrase:
    """
    When the LLM returns the exact "not found" phrase, generate_answer must
    return it unchanged. The route layer handles the HTTP 200 response; this
    function simply passes the LLM text through.
    """

    def test_llm_returns_not_found_phrase_passthrough(self, monkeypatch):
        """
        LLM returns the "not found" phrase → generate_answer returns it as-is.
        """
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key-for-testing")

        # Build a mock response whose .text attribute is the not-found phrase
        mock_response = MagicMock()
        mock_response.text = NOT_FOUND_PHRASE

        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response

        with patch(
            "services.generation.genai.GenerativeModel",
            return_value=mock_model_instance,
        ):
            result = generate_answer("What is the capital of Mars?", [make_chunk()])

        assert result == NOT_FOUND_PHRASE, (
            f"Expected generate_answer to return the not-found phrase verbatim.\n"
            f"Got: {result!r}"
        )


class TestGenerateAnswerGeminiAPIError:
    """
    When the Gemini API raises any exception during generation, generate_answer
    must re-raise it as GeminiAPIError.
    """

    def test_gemini_api_exception_raises_gemini_api_error(self, monkeypatch):
        """
        Gemini API error during generation → raises GeminiAPIError.
        """
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key-for-testing")

        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.side_effect = RuntimeError(
            "Simulated Gemini API network failure"
        )

        with patch(
            "services.generation.genai.GenerativeModel",
            return_value=mock_model_instance,
        ):
            with pytest.raises(GeminiAPIError) as exc_info:
                generate_answer("Tell me about the document.", [make_chunk()])

        assert "generation" in str(exc_info.value).lower() or "gemini" in str(exc_info.value).lower(), (
            f"GeminiAPIError message should identify the generation failure.\n"
            f"Got: {exc_info.value}"
        )
