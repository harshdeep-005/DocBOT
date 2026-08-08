"""
services/exceptions.py — Shared exception types for backend services.

GeminiAPIError is raised by the embeddings and generation services when the
Gemini API call fails (missing key, network error, unexpected API response).
The routes layer catches this and returns HTTP 502.

VectorStoreError is raised by vector_store.py when a Chroma write operation
fails. The routes layer catches this and returns HTTP 500.
"""


class GeminiAPIError(Exception):
    """
    Raised when a call to the Gemini API fails for any reason:
      - GEMINI_API_KEY absent or empty at invocation time (Requirement 5.2)
      - Network / transport error
      - Unexpected response from the Gemini API

    The routes layer maps this exception to HTTP 502 Bad Gateway.
    """


class VectorStoreError(Exception):
    """
    Raised when a Chroma vector store write operation fails for any reason:
      - collection.add() fails unexpectedly
      - Any other Chroma storage error

    The routes layer maps this exception to HTTP 500 Internal Server Error.
    """
