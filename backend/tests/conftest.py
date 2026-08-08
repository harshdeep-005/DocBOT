"""
tests/conftest.py — Shared pytest fixtures for the RAG Document Chatbot backend.

Fixtures provided:
  test_env      — Sets GEMINI_API_KEY and TOP_K_CHUNKS in the environment.
  test_client   — An httpx ASGI test client wrapping the FastAPI app.
  mock_gemini   — Patches google.generativeai embed_content and generate_content
                  so no real Gemini API calls are made during tests.

Key design note
---------------
main.py calls sys.exit(1) at module-import time when GEMINI_API_KEY is absent.
We therefore set the variable in os.environ BEFORE importing main, using
os.environ.setdefault so we don't clobber a value that another fixture may
have already written.
"""

import os

# Must happen before any import of main.py
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("TOP_K_CHUNKS", "5")

# Now safe to import the FastAPI app
from main import app  # noqa: E402

import pytest
import pytest_asyncio
import httpx
import chromadb
from chromadb.config import Settings
from unittest.mock import MagicMock, patch

import services.vector_store as _vs_module


# ── fixture: test_env ─────────────────────────────────────────────────────────

@pytest.fixture
def test_env(monkeypatch):
    """Ensure GEMINI_API_KEY and TOP_K_CHUNKS are set for the duration of a test."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("TOP_K_CHUNKS", "5")


# ── fixture: isolated in-memory vector store ─────────────────────────────────

@pytest.fixture(autouse=True)
def isolate_vector_store():
    """
    Replace the module-level Chroma client with a fresh in-memory client for
    every test, then restore the original after the test completes.

    This prevents tests from writing to the persistent .chroma directory and
    ensures each test starts with a clean store.
    """
    original_client = _vs_module._client
    in_memory = chromadb.Client(Settings(anonymized_telemetry=False))
    _vs_module._client = in_memory
    yield
    _vs_module._client = original_client


# ── fixture: test_client ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_client():
    """
    Async httpx test client backed by the FastAPI ASGI app.

    Uses httpx.ASGITransport so no real HTTP server is started.
    The client is created fresh for each test to keep state isolated.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ── fixture: mock_gemini ──────────────────────────────────────────────────────

@pytest.fixture
def mock_gemini():
    """
    Patch google.generativeai at the network boundary so no real Gemini calls
    are made.

    Patches applied:
      - services.embeddings.genai.embed_content
            → returns {"embedding": [0.1] * 768}
      - services.embeddings.genai.configure
            → no-op
      - services.generation.genai.configure
            → no-op
      - services.generation.genai.GenerativeModel
            → returns a mock whose generate_content() returns a response object
              with .text = "Test answer about the document."

    Yields
    ------
    dict with keys:
      "embed_content"    — the MagicMock for embed_content
      "generate_content" — the MagicMock for the model's generate_content method
    """
    fake_embedding = [0.1] * 768

    # Build a mock LLM response whose .text attribute is readable
    mock_response = MagicMock()
    mock_response.text = "Test answer about the document."

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    mock_embed = MagicMock(return_value={"embedding": fake_embedding})
    mock_generative_model_cls = MagicMock(return_value=mock_model)

    with (
        patch("services.embeddings.genai.configure"),
        patch("services.embeddings.genai.embed_content", mock_embed),
        patch("services.generation.genai.configure"),
        patch("services.generation.genai.GenerativeModel", mock_generative_model_cls),
    ):
        yield {
            "embed_content": mock_embed,
            "generate_content": mock_model.generate_content,
        }



# ── fixture: test_env ─────────────────────────────────────────────────────────

@pytest.fixture
def test_env(monkeypatch):
    """Ensure GEMINI_API_KEY and TOP_K_CHUNKS are set for the duration of a test."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("TOP_K_CHUNKS", "5")


# ── fixture: test_client ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_client():
    """
    Async httpx test client backed by the FastAPI ASGI app.

    Uses httpx.ASGITransport so no real HTTP server is started.
    The client is created fresh for each test to keep state isolated.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ── fixture: mock_gemini ──────────────────────────────────────────────────────

@pytest.fixture
def mock_gemini():
    """
    Patch google.generativeai at the network boundary so no real Gemini calls
    are made.

    Patches applied:
      - services.embeddings.genai.embed_content
            → returns {"embedding": [0.1] * 768}
      - services.embeddings.genai.configure
            → no-op
      - services.generation.genai.configure
            → no-op
      - services.generation.genai.GenerativeModel
            → returns a mock whose generate_content() returns a response object
              with .text = "Test answer about the document."

    Yields
    ------
    dict with keys:
      "embed_content"    — the MagicMock for embed_content
      "generate_content" — the MagicMock for the model's generate_content method
    """
    fake_embedding = [0.1] * 768

    # Build a mock LLM response whose .text attribute is readable
    mock_response = MagicMock()
    mock_response.text = "Test answer about the document."

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    mock_embed = MagicMock(return_value={"embedding": fake_embedding})
    mock_generative_model_cls = MagicMock(return_value=mock_model)

    with (
        patch("services.embeddings.genai.configure"),
        patch("services.embeddings.genai.embed_content", mock_embed),
        patch("services.generation.genai.configure"),
        patch("services.generation.genai.GenerativeModel", mock_generative_model_cls),
    ):
        yield {
            "embed_content": mock_embed,
            "generate_content": mock_model.generate_content,
        }
