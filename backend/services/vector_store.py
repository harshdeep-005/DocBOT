"""
services/vector_store.py — Vector Store (Chroma)

Manages chunk storage and retrieval using an embedded Chroma collection.

Public API
----------
replace_document_chunks(document_id, chunks, embeddings) -> None
    Atomically replaces all existing chunks for document_id with the new ones.
    Deletes old records first, then bulk-inserts new records in one add() call.
    Raises VectorStoreError on write failure.

similarity_search(document_id, query_embedding, top_k) -> List[Chunk]
    Returns the top_k most similar chunks scoped to document_id.
    Returns an empty list when no chunks exist for the document_id.

rollback_document(document_id) -> None
    Best-effort delete of all chunks for document_id.
    Catches and logs Chroma errors; never re-raises.

Requirements: 5.3, 5.4, 5.7, 10.1, 10.2
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.config import Settings

from models.schemas import Chunk, FileType
from services.exceptions import VectorStoreError

logger = logging.getLogger(__name__)

# ── Chroma client and collection (module-level singleton) ─────────────────────

# Persistent storage directory — sits next to this file's package root.
# Override CHROMA_PERSIST_DIR env var to change the location.
_DEFAULT_PERSIST_DIR = str(
    Path(__file__).parent.parent / ".chroma"
)

_client: Optional[chromadb.ClientAPI] = None
_COLLECTION_NAME = "document_chunks"


def _get_collection() -> chromadb.Collection:
    """Return (or lazily create) the shared Chroma collection."""
    global _client
    if _client is None:
        persist_dir = os.environ.get("CHROMA_PERSIST_DIR", _DEFAULT_PERSIST_DIR)
        _client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── File types that carry no location ────────────────────────────────────────

_NO_LOCATION_TYPES = {FileType.TXT, FileType.MD}


def _build_metadata(chunk: Chunk) -> dict:
    """
    Build the Chroma metadata dict for a single chunk.

    location is OMITTED entirely for TXT/MD chunks (never stored as null
    or empty string) per Requirements 5.3 and 10.1.
    """
    meta: dict = {
        "document_id": chunk.document_id,
        "file_type": chunk.file_type.value,
    }
    if chunk.file_type not in _NO_LOCATION_TYPES and chunk.location is not None:
        meta["location"] = chunk.location
    return meta


def _metadata_to_chunk(chunk_id: str, text: str, metadata: dict) -> Chunk:
    """Reconstruct a Chunk from a Chroma query result row."""
    file_type = FileType(metadata["file_type"])
    location: Optional[int] = metadata.get("location")  # absent for TXT/MD
    return Chunk(
        chunk_id=chunk_id,
        document_id=metadata["document_id"],
        file_type=file_type,
        text=text,
        location=location,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def replace_document_chunks(
    document_id: str,
    chunks: List[Chunk],
    embeddings: List[List[float]],
) -> None:
    """
    Atomically replace all existing chunks for document_id.

    Strategy (Requirement 5.4):
      1. Delete all existing records for document_id.
      2. Bulk-insert all new records in a single collection.add() call.

    Raises
    ------
    VectorStoreError
        If the bulk-insert call fails for any reason (Requirement 5.7).
    """
    collection = _get_collection()

    # Step 1 — delete existing records for this document_id.
    # We swallow delete errors here intentionally: if the document never
    # existed (first upload), Chroma may return an empty result without error,
    # which is fine. Any delete error is not fatal to the insert.
    try:
        collection.delete(where={"document_id": document_id})
    except Exception as exc:
        logger.warning(
            "Non-fatal error while deleting old chunks for document_id=%r: %s",
            document_id,
            exc,
        )

    if not chunks:
        return

    # Step 2 — bulk-insert all new records in one call.
    ids = [chunk.chunk_id for chunk in chunks]
    documents = [chunk.text for chunk in chunks]
    metadatas = [_build_metadata(chunk) for chunk in chunks]

    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
    except Exception as exc:
        logger.error(
            "Vector store write failed for document_id=%r: %s",
            document_id,
            exc,
        )
        raise VectorStoreError(
            f"Storage failure: {exc}"
        ) from exc


def similarity_search(
    document_id: str,
    query_embedding: List[float],
    top_k: int,
) -> List[Chunk]:
    """
    Return the top_k most similar chunks scoped to document_id.

    Returns an empty list when no chunks exist for the document_id
    (Requirement 10.2).
    """
    collection = _get_collection()

    # Guard: if the collection is empty for this document_id, return early.
    try:
        count = collection.count()
    except Exception:
        return []

    if count == 0:
        return []

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"document_id": document_id},
            include=["documents", "metadatas", "embeddings"],
        )
    except Exception as exc:
        # If Chroma raises (e.g. no matching records at all), return empty list.
        logger.warning(
            "similarity_search raised for document_id=%r (returning []): %s",
            document_id,
            exc,
        )
        return []

    ids_list = results.get("ids", [[]])[0]
    documents_list = results.get("documents", [[]])[0]
    metadatas_list = results.get("metadatas", [[]])[0]

    if not ids_list:
        return []

    chunks: List[Chunk] = []
    for chunk_id, text, metadata in zip(ids_list, documents_list, metadatas_list):
        chunks.append(_metadata_to_chunk(chunk_id, text, metadata))

    return chunks


def rollback_document(document_id: str) -> None:
    """
    Best-effort delete of all chunks for document_id.

    Catches and logs any Chroma errors; never re-raises (Requirement 5.5 /
    design rollback strategy).
    """
    try:
        collection = _get_collection()
        collection.delete(where={"document_id": document_id})
        logger.info("Rolled back chunks for document_id=%r", document_id)
    except Exception as exc:
        logger.error(
            "Rollback failed for document_id=%r (best-effort, suppressed): %s",
            document_id,
            exc,
        )
