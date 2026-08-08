"""
Property-based tests for services/vector_store.py

Property 13: Chunk Metadata Round-Trip Fidelity
  Validates: Requirements 5.3, 10.1

Property 14: Atomic Replacement — Post-Ingestion Query Reflects Only New Chunks
  Validates: Requirements 5.4

Property 16: Retrieval Is Scoped to the Queried Document_ID
  Validates: Requirements 6.4, 10.2
"""

import uuid
from typing import List, Optional

import chromadb
import pytest
from chromadb.config import Settings
from hypothesis import given, settings
from hypothesis import strategies as st

from models.schemas import Chunk, FileType
import services.vector_store as vs_module
from services.vector_store import (
    replace_document_chunks,
    rollback_document,
    similarity_search,
)


# ── Test helpers ──────────────────────────────────────────────────────────────

def _make_embedding(dim: int = 8) -> List[float]:
    """Return a deterministic unit-ish embedding vector."""
    val = 1.0 / dim
    return [val] * dim


def _make_chunk(
    document_id: str,
    file_type: FileType,
    text: str,
    location: Optional[int] = None,
) -> Chunk:
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id=document_id,
        file_type=file_type,
        text=text,
        location=location,
    )


def _fresh_collection():
    """Create a brand-new in-memory Chroma collection with a unique name."""
    client = chromadb.Client(Settings(anonymized_telemetry=False))
    collection_name = f"test_{uuid.uuid4().hex}"
    return client, client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


# ── Hypothesis strategies ─────────────────────────────────────────────────────

_safe_text = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
        whitelist_characters=" .-_",
    ),
)

_doc_id_strategy = st.text(
    min_size=1,
    max_size=40,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="-_",
    ),
)

_pdf_like_file_types = st.sampled_from([FileType.PDF, FileType.DOCX, FileType.PPTX])
_no_location_file_types = st.sampled_from([FileType.TXT, FileType.MD])
_any_file_type = st.sampled_from(list(FileType))


# ── Property 13 ───────────────────────────────────────────────────────────────

@given(
    document_id=_doc_id_strategy,
    file_type=_any_file_type,
    text=_safe_text,
    location=st.one_of(st.none(), st.integers(min_value=1, max_value=500)),
)
@settings(max_examples=100)
def test_property_13_chunk_metadata_round_trip_fidelity(
    document_id: str,
    file_type: FileType,
    text: str,
    location: Optional[int],
):
    """
    **Validates: Requirements 5.3, 10.1**

    Property 13: Chunk Metadata Round-Trip Fidelity
    - Storing a Chunk and then retrieving it must yield byte-for-byte identical
      document_id, file_type, text, and location values.
    - TXT/MD chunks must have no location key in the retrieved record
      (location must be None, never a stored null or empty string).
    """
    # For TXT/MD file types, location is meaningless; always treat as None.
    if file_type in (FileType.TXT, FileType.MD):
        location = None

    chunk = _make_chunk(document_id, file_type, text, location)
    embedding = _make_embedding()

    # Use a fresh in-memory collection for isolation.
    client, collection = _fresh_collection()

    # Temporarily redirect the module to use our isolated collection.
    original_get_collection = vs_module._get_collection

    def _isolated_collection():
        return collection

    vs_module._get_collection = _isolated_collection
    try:
        replace_document_chunks(document_id, [chunk], [embedding])
        results = similarity_search(document_id, embedding, top_k=1)
    finally:
        vs_module._get_collection = original_get_collection

    assert len(results) == 1, (
        f"Expected 1 result for document_id={document_id!r}, got {len(results)}"
    )

    retrieved = results[0]

    # Byte-for-byte field checks
    assert retrieved.chunk_id == chunk.chunk_id, (
        f"chunk_id mismatch: stored={chunk.chunk_id!r}, retrieved={retrieved.chunk_id!r}"
    )
    assert retrieved.document_id == chunk.document_id, (
        f"document_id mismatch: stored={chunk.document_id!r}, retrieved={retrieved.document_id!r}"
    )
    assert retrieved.file_type == chunk.file_type, (
        f"file_type mismatch: stored={chunk.file_type!r}, retrieved={retrieved.file_type!r}"
    )
    assert retrieved.text == chunk.text, (
        f"text mismatch: stored={chunk.text!r}, retrieved={retrieved.text!r}"
    )

    if file_type in (FileType.TXT, FileType.MD):
        # TXT/MD: location must be absent (None), never stored as null/empty
        assert retrieved.location is None, (
            f"TXT/MD chunk must have no location, got {retrieved.location!r}"
        )
    else:
        assert retrieved.location == chunk.location, (
            f"location mismatch: stored={chunk.location!r}, retrieved={retrieved.location!r}"
        )


# ── Property 14 ───────────────────────────────────────────────────────────────

@given(
    document_id=_doc_id_strategy,
    old_texts=st.lists(_safe_text, min_size=1, max_size=5),
    new_texts=st.lists(_safe_text, min_size=1, max_size=5),
)
@settings(max_examples=100)
def test_property_14_atomic_replacement(
    document_id: str,
    old_texts: List[str],
    new_texts: List[str],
):
    """
    **Validates: Requirements 5.4**

    Property 14: Atomic Replacement — Post-Ingestion Query Reflects Only New Chunks
    - After a second ingestion for the same document_id, similarity search must
      return only chunks from the new set; no chunk from the old set may appear.
    """
    # Build two distinct sets of chunks for the same document_id.
    old_chunks = [
        _make_chunk(document_id, FileType.TXT, text) for text in old_texts
    ]
    new_chunks = [
        _make_chunk(document_id, FileType.TXT, text) for text in new_texts
    ]

    embedding = _make_embedding()
    old_embeddings = [embedding] * len(old_chunks)
    new_embeddings = [embedding] * len(new_chunks)

    client, collection = _fresh_collection()
    original_get_collection = vs_module._get_collection

    def _isolated_collection():
        return collection

    vs_module._get_collection = _isolated_collection
    try:
        # First ingestion
        replace_document_chunks(document_id, old_chunks, old_embeddings)
        # Second ingestion (atomic replacement)
        replace_document_chunks(document_id, new_chunks, new_embeddings)

        # Query with a high top_k to retrieve everything
        top_k = len(old_chunks) + len(new_chunks) + 10
        results = similarity_search(document_id, embedding, top_k=top_k)
    finally:
        vs_module._get_collection = original_get_collection

    result_ids = {c.chunk_id for c in results}
    old_ids = {c.chunk_id for c in old_chunks}
    new_ids = {c.chunk_id for c in new_chunks}

    # No old chunk may appear in results
    stale_ids = result_ids & old_ids
    assert not stale_ids, (
        f"Stale (old) chunk IDs found after replacement: {stale_ids}. "
        f"Only new chunk IDs should be present: {new_ids}"
    )

    # All new chunks must be present
    missing_new = new_ids - result_ids
    assert not missing_new, (
        f"New chunk IDs missing from results after replacement: {missing_new}"
    )


# ── Property 16 ───────────────────────────────────────────────────────────────

@given(
    doc_ids=st.lists(
        _doc_id_strategy,
        min_size=2,
        max_size=4,
        unique=True,
    ),
    texts_per_doc=st.lists(_safe_text, min_size=1, max_size=3),
)
@settings(max_examples=100)
def test_property_16_retrieval_scoped_to_document_id(
    doc_ids: List[str],
    texts_per_doc: List[str],
):
    """
    **Validates: Requirements 6.4, 10.2**

    Property 16: Retrieval Is Scoped to the Queried Document_ID
    - Storing chunks for multiple document_ids simultaneously, then querying
      for a specific document_id must return only chunks carrying that exact
      document_id — cross-document results must never appear.
    """
    embedding = _make_embedding()

    client, collection = _fresh_collection()
    original_get_collection = vs_module._get_collection

    def _isolated_collection():
        return collection

    vs_module._get_collection = _isolated_collection
    try:
        # Store chunks for every document_id
        for doc_id in doc_ids:
            chunks = [
                _make_chunk(doc_id, FileType.TXT, text) for text in texts_per_doc
            ]
            embeddings = [embedding] * len(chunks)
            replace_document_chunks(doc_id, chunks, embeddings)

        # For each document_id, assert results are scoped
        for queried_id in doc_ids:
            top_k = len(doc_ids) * len(texts_per_doc) + 10
            results = similarity_search(queried_id, embedding, top_k=top_k)

            for chunk in results:
                assert chunk.document_id == queried_id, (
                    f"Cross-document contamination: queried document_id={queried_id!r} "
                    f"but got chunk with document_id={chunk.document_id!r}"
                )
    finally:
        vs_module._get_collection = original_get_collection
