from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"
    MD = "md"


class TextSegment(BaseModel):
    """Raw text unit produced by an extractor."""
    text: str
    location: Optional[int] = None   # 1-based page/slide; absent for TXT/MD


class Chunk(BaseModel):
    """A processed, embeddable unit of text with full provenance metadata."""
    chunk_id: str                    # UUID4, assigned at chunking time
    document_id: str
    file_type: FileType
    text: str
    location: Optional[int] = None  # absent (not null) for TXT/MD


class Citation(BaseModel):
    """A deduplicated source reference for display in the frontend."""
    label: str                       # "Page N" or "Slide N"
    location: int


class UploadResponse(BaseModel):
    document_id: str
    chunk_count: int


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    document_id: str


class SourceChunk(BaseModel):
    """A retrieved chunk returned to the frontend."""
    rank: int                        # 1-based retrieval rank
    text: str
    citation: Optional[Citation] = None


class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]        # deduplicated, ordered by location
    chunks: List[SourceChunk]
