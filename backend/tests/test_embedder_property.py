"""
Property-based tests for services/embeddings.py

Property 12: Embedder Is Called Exactly Once per Chunk
  Validates: Requirements 5.1
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from services.embeddings import embed_texts


@given(st.lists(st.text(), min_size=1))
@settings(max_examples=100)
def test_property_12_embedder_call_count(texts: list):
    """
    **Validates: Requirements 5.1**

    Property 12: Embedder Is Called Exactly Once per Chunk
    - For any list of N texts passed to embed_texts(), the Gemini
      embed_content API must be called exactly N times — once per text,
      no more, no less.
    """
    n = len(texts)

    # Build a fake embedding return value: a 3-element float vector.
    # The actual values don't matter; we're only testing call count.
    fake_embedding = [0.1, 0.2, 0.3]
    mock_embed_content = MagicMock(return_value={"embedding": fake_embedding})

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        with patch("services.embeddings.genai.configure"):
            with patch(
                "services.embeddings.genai.embed_content",
                side_effect=mock_embed_content,
            ):
                result = embed_texts(texts)

    assert mock_embed_content.call_count == n, (
        f"Expected embed_content to be called {n} times (once per text), "
        f"but it was called {mock_embed_content.call_count} times. "
        f"Input had {n} text(s)."
    )
    assert len(result) == n, (
        f"Expected {n} embeddings in the result, got {len(result)}."
    )
