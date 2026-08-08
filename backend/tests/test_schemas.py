"""
Unit tests for schema validation edge cases.
Requirements: 6.9
"""

import pytest
from pydantic import ValidationError

from models.schemas import AskRequest, Chunk, FileType


# ---------------------------------------------------------------------------
# AskRequest – question field validation
# ---------------------------------------------------------------------------

class TestAskRequestValidation:
    """Tests for AskRequest schema validation."""

    def test_empty_question_raises_validation_error(self):
        """AskRequest rejects an empty string (min_length=1)."""
        with pytest.raises(ValidationError):
            AskRequest(question="", document_id="doc-123")

    def test_question_too_long_raises_validation_error(self):
        """AskRequest rejects a question longer than 2000 characters (max_length=2000)."""
        long_question = "a" * 2001
        with pytest.raises(ValidationError):
            AskRequest(question=long_question, document_id="doc-123")

    def test_single_char_question_is_valid(self):
        """AskRequest accepts a one-character question (boundary: min_length=1)."""
        req = AskRequest(question="a", document_id="doc-123")
        assert req.question == "a"
        assert req.document_id == "doc-123"

    def test_max_length_question_is_valid(self):
        """AskRequest accepts a question of exactly 2000 characters (boundary: max_length=2000)."""
        max_question = "a" * 2000
        req = AskRequest(question=max_question, document_id="doc-123")
        assert len(req.question) == 2000

    def test_missing_document_id_raises_validation_error(self):
        """AskRequest requires document_id field."""
        with pytest.raises(ValidationError):
            AskRequest(question="What is this document about?")

    def test_missing_question_raises_validation_error(self):
        """AskRequest requires question field."""
        with pytest.raises(ValidationError):
            AskRequest(document_id="doc-123")


# ---------------------------------------------------------------------------
# Chunk – location field (Optional[int])
# ---------------------------------------------------------------------------

class TestChunkValidation:
    """Tests for Chunk schema validation, focusing on the optional location field."""

    def test_chunk_without_location_defaults_to_none(self):
        """Chunk location defaults to None — valid for TXT/MD file types."""
        chunk = Chunk(
            chunk_id="chunk-uuid-001",
            document_id="doc-123",
            file_type=FileType.TXT,
            text="Some plain text content.",
        )
        assert chunk.location is None

    def test_chunk_with_location_none_explicit(self):
        """Chunk accepts explicit location=None — valid for TXT/MD file types."""
        chunk = Chunk(
            chunk_id="chunk-uuid-002",
            document_id="doc-123",
            file_type=FileType.MD,
            text="Some markdown content.",
            location=None,
        )
        assert chunk.location is None

    def test_chunk_with_valid_location_integer(self):
        """Chunk stores a valid page/slide location integer — valid for PDF/DOCX/PPTX."""
        chunk = Chunk(
            chunk_id="chunk-uuid-003",
            document_id="doc-456",
            file_type=FileType.PDF,
            text="Content from page 5.",
            location=5,
        )
        assert chunk.location == 5

    def test_chunk_with_location_one(self):
        """Chunk accepts location=1 (first page/slide)."""
        chunk = Chunk(
            chunk_id="chunk-uuid-004",
            document_id="doc-789",
            file_type=FileType.PPTX,
            text="Content from slide 1.",
            location=1,
        )
        assert chunk.location == 1

    def test_chunk_all_required_fields_present(self):
        """Chunk stores all provided fields correctly."""
        chunk = Chunk(
            chunk_id="chunk-uuid-005",
            document_id="doc-321",
            file_type=FileType.DOCX,
            text="Some docx content.",
            location=3,
        )
        assert chunk.chunk_id == "chunk-uuid-005"
        assert chunk.document_id == "doc-321"
        assert chunk.file_type == FileType.DOCX
        assert chunk.text == "Some docx content."
        assert chunk.location == 3
