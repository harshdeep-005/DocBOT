"""
Unit tests for services/embeddings.py

Requirements: 5.2, 5.5
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from services.embeddings import embed_texts, embed_single
from services.exceptions import GeminiAPIError


# ── Test 1: Gemini API error mid-ingestion → GeminiAPIError with chunk index ──
# Validates: Requirement 5.5

class TestGeminiAPIErrorMidIngestion:

    def test_api_error_on_first_chunk_raises_gemini_api_error(self):
        """
        When the Gemini API raises an exception on the very first chunk (index 0),
        embed_texts must re-raise it as GeminiAPIError and include the chunk index
        and the original error reason in the message.
        """
        texts = ["chunk zero", "chunk one", "chunk two"]

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("services.embeddings.genai.configure"):
                with patch(
                    "services.embeddings.genai.embed_content",
                    side_effect=RuntimeError("rate limit exceeded"),
                ):
                    with pytest.raises(GeminiAPIError) as exc_info:
                        embed_texts(texts)

        error_message = str(exc_info.value)
        assert "0" in error_message, (
            f"Error message must contain the failing chunk index (0). Got: {error_message!r}"
        )
        assert "rate limit exceeded" in error_message, (
            f"Error message must contain the original API error reason. Got: {error_message!r}"
        )

    def test_api_error_on_middle_chunk_raises_with_correct_index(self):
        """
        When the Gemini API succeeds for the first two chunks but fails on
        chunk index 2, the raised GeminiAPIError must report index 2 in its
        message.
        """
        texts = ["chunk zero", "chunk one", "chunk two fails", "chunk three"]
        fake_embedding = [0.1, 0.2, 0.3]

        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 3:
                raise RuntimeError("upstream timeout")
            return {"embedding": fake_embedding}

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("services.embeddings.genai.configure"):
                with patch(
                    "services.embeddings.genai.embed_content",
                    side_effect=side_effect,
                ):
                    with pytest.raises(GeminiAPIError) as exc_info:
                        embed_texts(texts)

        error_message = str(exc_info.value)
        assert "2" in error_message, (
            f"Error message must contain failing chunk index 2. Got: {error_message!r}"
        )
        assert "upstream timeout" in error_message, (
            f"Error message must contain the original API reason. Got: {error_message!r}"
        )

    def test_api_error_on_last_chunk_raises_gemini_api_error(self):
        """
        An API failure on the last chunk must also be wrapped in GeminiAPIError
        with the correct (last) index.
        """
        texts = ["chunk zero", "chunk one", "chunk two"]
        fake_embedding = [0.1, 0.2, 0.3]
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 3:
                raise Exception("quota exceeded")
            return {"embedding": fake_embedding}

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("services.embeddings.genai.configure"):
                with patch(
                    "services.embeddings.genai.embed_content",
                    side_effect=side_effect,
                ):
                    with pytest.raises(GeminiAPIError) as exc_info:
                        embed_texts(texts)

        error_message = str(exc_info.value)
        assert "2" in error_message, (
            f"Error message must contain last chunk index (2). Got: {error_message!r}"
        )
        assert "quota exceeded" in error_message, (
            f"Error message must contain the original reason. Got: {error_message!r}"
        )

    def test_gemini_api_error_type_is_correct(self):
        """
        The exception raised by embed_texts on an API failure must be an
        instance of GeminiAPIError (not a plain RuntimeError or other type).
        """
        texts = ["only chunk"]

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("services.embeddings.genai.configure"):
                with patch(
                    "services.embeddings.genai.embed_content",
                    side_effect=RuntimeError("network error"),
                ):
                    with pytest.raises(GeminiAPIError):
                        embed_texts(texts)

    def test_partial_success_aborted_on_error(self):
        """
        When embed_texts fails mid-ingestion, it must not return a partial
        result — the exception must be raised, not a list with fewer items.
        """
        texts = ["ok chunk", "bad chunk"]
        fake_embedding = [0.1, 0.2, 0.3]
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("api down")
            return {"embedding": fake_embedding}

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("services.embeddings.genai.configure"):
                with patch(
                    "services.embeddings.genai.embed_content",
                    side_effect=side_effect,
                ):
                    with pytest.raises(GeminiAPIError):
                        result = embed_texts(texts)
                        # Should never reach here
                        assert False, f"Expected GeminiAPIError but got result: {result}"


# ── Test 2: GEMINI_API_KEY absent → GeminiAPIError raised ────────────────────
# Validates: Requirement 5.2

class TestMissingAPIKey:

    def test_missing_key_raises_gemini_api_error(self):
        """
        When GEMINI_API_KEY is not present in the environment, embed_texts
        must raise GeminiAPIError before making any API call.
        """
        env_without_key = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}

        with patch.dict(os.environ, env_without_key, clear=True):
            with patch("services.embeddings.genai.embed_content") as mock_embed:
                with pytest.raises(GeminiAPIError):
                    embed_texts(["some text"])

                # The API must never be called when the key is absent
                mock_embed.assert_not_called()

    def test_empty_key_raises_gemini_api_error(self):
        """
        An empty GEMINI_API_KEY (set but blank) must also raise GeminiAPIError
        without making any API call.
        """
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            with patch("services.embeddings.genai.embed_content") as mock_embed:
                with pytest.raises(GeminiAPIError):
                    embed_texts(["some text"])

                mock_embed.assert_not_called()

    def test_whitespace_only_key_raises_gemini_api_error(self):
        """
        A GEMINI_API_KEY that is only whitespace must be treated as absent
        and raise GeminiAPIError without making any API call.
        """
        with patch.dict(os.environ, {"GEMINI_API_KEY": "   "}, clear=False):
            with patch("services.embeddings.genai.embed_content") as mock_embed:
                with pytest.raises(GeminiAPIError):
                    embed_texts(["some text"])

                mock_embed.assert_not_called()

    def test_missing_key_error_message_is_descriptive(self):
        """
        The GeminiAPIError raised for a missing API key must include a
        meaningful message indicating the key is not configured.
        """
        env_without_key = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}

        with patch.dict(os.environ, env_without_key, clear=True):
            with pytest.raises(GeminiAPIError) as exc_info:
                embed_texts(["some text"])

        error_message = str(exc_info.value).lower()
        # Message should indicate the API key is the problem
        assert "gemini_api_key" in error_message or "api key" in error_message, (
            f"Error message should mention the API key. Got: {str(exc_info.value)!r}"
        )

    def test_missing_key_also_raises_for_embed_single(self):
        """
        embed_single (which delegates to embed_texts) must also raise
        GeminiAPIError when the key is absent.
        """
        env_without_key = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}

        with patch.dict(os.environ, env_without_key, clear=True):
            with pytest.raises(GeminiAPIError):
                embed_single("some text")
