"""
Unit tests for services/vector_store.py

Requirements: 5.4, 5.5, 5.7

Test scenarios:
  1. replace_document_chunks raises VectorStoreError on write failure.
  2. rollback_document is called after a VectorStoreError (rollback attempted).
  3. Rollback failure does not suppress the original VectorStoreError / HTTP 500.
  4. similarity_search returns empty list when no chunks exist for document_id.
"""

import uuid
from typing import List
from unittest.mock import MagicMock, patch

import chromadb
import pytest
from chromadb.config import Settings

import services.vector_store as vs_module
from models.schemas import Chunk, FileType
from services.exceptions import VectorStoreError
from services.vector_store import (
    replace_document_chunks,
    rollback_document,
    similarity_search,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_chunk(
    document_id: str = "doc-unit-test",
    file_type: FileType = FileType.TXT,
    text: str = "sample chunk text",
    location: int | None = None,
) -> Chunk:
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id=document_id,
        file_type=file_type,
        text=text,
        location=location,
    )


def _make_embedding() -> List[float]:
    return [0.1, 0.2, 0.3, 0.4]


def _fresh_collection():
    """Return a brand-new isolated in-memory Chroma collection."""
    client = chromadb.Client(Settings(anonymized_telemetry=False))
    name = f"unit_{uuid.uuid4().hex}"
    return client, client.get_or_create_collection(name=name)


# ── Fixture: isolated in-memory collection ───────────────────────────────────

class IsolatedVectorStore:
    """Context manager that redirects the module to an isolated collection."""

    def __init__(self):
        self.client = None
        self.collection = None
        self._original = None

    def __enter__(self):
        self.client, self.collection = _fresh_collection()
        self._original = vs_module._get_collection

        collection = self.collection

        def _isolated():
            return collection

        vs_module._get_collection = _isolated
        return self

    def __exit__(self, *_):
        vs_module._get_collection = self._original


# ── Test 1: VectorStoreError raised on write failure ─────────────────────────
# Validates: Requirement 5.7

class TestReplaceDocumentChunksWriteError:

    def test_write_failure_raises_vector_store_error(self):
        """
        When collection.add() raises, replace_document_chunks must raise
        VectorStoreError with a message containing 'Storage failure'.
        """
        chunk = _make_chunk()
        embedding = _make_embedding()

        mock_collection = MagicMock()
        mock_collection.delete.return_value = None
        mock_collection.add.side_effect = RuntimeError("disk full")

        with patch.object(vs_module, "_get_collection", return_value=mock_collection):
            with pytest.raises(VectorStoreError) as exc_info:
                replace_document_chunks("doc-1", [chunk], [embedding])

        assert "Storage failure" in str(exc_info.value), (
            f"Expected 'Storage failure' in error message, got: {exc_info.value!r}"
        )

    def test_write_failure_error_message_includes_cause(self):
        """
        The VectorStoreError message must include the original cause string.
        """
        chunk = _make_chunk()
        embedding = _make_embedding()

        mock_collection = MagicMock()
        mock_collection.delete.return_value = None
        mock_collection.add.side_effect = RuntimeError("connection refused")

        with patch.object(vs_module, "_get_collection", return_value=mock_collection):
            with pytest.raises(VectorStoreError) as exc_info:
                replace_document_chunks("doc-2", [chunk], [embedding])

        assert "connection refused" in str(exc_info.value), (
            f"Expected original cause in error message, got: {exc_info.value!r}"
        )

    def test_vector_store_error_type_is_correct(self):
        """
        The exception raised must be an instance of VectorStoreError, not a
        plain RuntimeError or other exception type.
        """
        chunk = _make_chunk()
        embedding = _make_embedding()

        mock_collection = MagicMock()
        mock_collection.delete.return_value = None
        mock_collection.add.side_effect = Exception("unexpected error")

        with patch.object(vs_module, "_get_collection", return_value=mock_collection):
            with pytest.raises(VectorStoreError):
                replace_document_chunks("doc-3", [chunk], [embedding])


# ── Test 2: Rollback is attempted after VectorStoreError ─────────────────────
# Validates: Requirement 5.7 / design rollback strategy

class TestRollbackAttemptedAfterWriteError:
    """
    Simulates the route-layer pattern: when replace_document_chunks raises
    VectorStoreError the caller should invoke rollback_document and the
    original error must still propagate as HTTP 500.

    These tests validate that:
      a) rollback_document can be called without raising when Chroma works.
      b) rollback_document swallows its own errors (best-effort).
      c) The original VectorStoreError is not suppressed by a rollback failure.
    """

    def test_rollback_called_after_write_error_does_not_raise(self):
        """
        When a write error occurs, calling rollback_document must not itself
        raise — it is best-effort.
        """
        doc_id = "doc-rollback-1"
        chunk = _make_chunk(document_id=doc_id)
        embedding = _make_embedding()

        # First: populate the collection so there is something to delete.
        with IsolatedVectorStore() as store:
            # Force a write error on add
            original_add = store.collection.add
            store.collection.add = MagicMock(side_effect=RuntimeError("write fail"))

            with pytest.raises(VectorStoreError):
                replace_document_chunks(doc_id, [chunk], [embedding])

            # Restore add so rollback (delete) can work
            store.collection.add = original_add

            # Rollback must complete silently
            rollback_document(doc_id)  # should not raise

    def test_rollback_failure_does_not_suppress_original_error(self):
        """
        Even if rollback_document itself encounters a Chroma error, the
        original VectorStoreError (or HTTP 500 response) must still be
        returned — rollback failure must be swallowed, not re-raised.

        This test simulates the route-handler pattern:
            try:
                replace_document_chunks(...)
            except VectorStoreError:
                rollback_document(...)   # may itself fail
                raise                    # original error re-raised
        """
        doc_id = "doc-rollback-fail"
        chunk = _make_chunk(document_id=doc_id)
        embedding = _make_embedding()

        failing_collection = MagicMock()
        failing_collection.delete.side_effect = RuntimeError("delete also broken")
        failing_collection.add.side_effect = RuntimeError("write broken")

        with patch.object(vs_module, "_get_collection", return_value=failing_collection):
            original_error = None
            try:
                replace_document_chunks(doc_id, [chunk], [embedding])
            except VectorStoreError as exc:
                original_error = exc
                # Route layer calls rollback; it must not raise
                rollback_document(doc_id)  # should not raise even though delete fails

            assert original_error is not None, (
                "Expected VectorStoreError to be raised by replace_document_chunks"
            )
            assert isinstance(original_error, VectorStoreError), (
                f"Expected VectorStoreError, got {type(original_error)}"
            )


# ── Test 3: Similarity search returns empty list for unknown document_id ──────
# Validates: Requirement 10.2

class TestSimilaritySearchNoResults:

    def test_search_unknown_document_id_returns_empty_list(self):
        """
        When no chunks have been stored for a document_id, similarity_search
        must return an empty list (not raise, not return None).
        """
        query_embedding = _make_embedding()

        with IsolatedVectorStore():
            results = similarity_search("unknown-doc-id", query_embedding, top_k=5)

        assert results == [], (
            f"Expected empty list for unknown document_id, got: {results!r}"
        )

    def test_search_different_document_id_returns_empty_list(self):
        """
        When chunks are stored for document_id A, querying for document_id B
        must return an empty list.
        """
        chunk_a = _make_chunk(document_id="doc-A", text="content for document A")
        embedding = _make_embedding()

        with IsolatedVectorStore():
            replace_document_chunks("doc-A", [chunk_a], [embedding])
            results = similarity_search("doc-B", embedding, top_k=5)

        assert results == [], (
            f"Expected empty list when querying doc-B (only doc-A exists), got: {results!r}"
        )

    def test_search_empty_collection_returns_empty_list(self):
        """
        Querying an entirely empty collection must return an empty list.
        """
        query_embedding = _make_embedding()

        with IsolatedVectorStore():
            results = similarity_search("any-doc-id", query_embedding, top_k=10)

        assert results == [], (
            f"Expected empty list from empty collection, got: {results!r}"
        )

    def test_search_returns_list_type(self):
        """
        The return type of similarity_search must always be a list, even when
        no results are found.
        """
        query_embedding = _make_embedding()

        with IsolatedVectorStore():
            results = similarity_search("no-such-doc", query_embedding, top_k=1)

        assert isinstance(results, list), (
            f"similarity_search must return a list, got {type(results)}"
        )


# ── Test 4: Rollback best-effort — errors are not re-raised ──────────────────
# Validates: Requirement 5.5 / design rollback strategy

class TestRollbackBestEffort:

    def test_rollback_does_not_raise_on_chroma_error(self):
        """
        rollback_document must never propagate Chroma exceptions; it must
        catch and log them silently.
        """
        failing_collection = MagicMock()
        failing_collection.delete.side_effect = RuntimeError("chroma internal error")

        with patch.object(vs_module, "_get_collection", return_value=failing_collection):
            # Must not raise
            rollback_document("doc-to-rollback")

    def test_rollback_succeeds_on_valid_document(self):
        """
        rollback_document for an existing document_id must complete without
        raising and remove the chunks from the store.
        """
        doc_id = "doc-to-delete"
        chunk = _make_chunk(document_id=doc_id)
        embedding = _make_embedding()

        with IsolatedVectorStore():
            replace_document_chunks(doc_id, [chunk], [embedding])
            rollback_document(doc_id)

            # After rollback, search must return empty
            results = similarity_search(doc_id, embedding, top_k=5)
            assert results == [], (
                f"Expected empty results after rollback, got: {results!r}"
            )
