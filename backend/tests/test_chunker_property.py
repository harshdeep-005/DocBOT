"""
Property-based tests for services/chunking.py

Property 10: Chunk Word Limit and Overlap Invariant
  Validates: Requirements 4.1, 4.2

Property 11: Chunker Attaches Complete Metadata to Every Chunk
  Validates: Requirements 4.5, 5.3, 10.1
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from models.schemas import FileType, TextSegment
from services.chunking import chunk_segments


# ── helpers ───────────────────────────────────────────────────────────────────

def _word_count(text: str) -> int:
    return len(text.split())


def _overlap_word_count(text_a: str, text_b: str) -> int:
    """
    Count how many words from the end of *text_a* appear (in order) at the
    start of *text_b*.  We compare word-by-word from the potential overlap
    boundary.
    """
    words_a = text_a.split()
    words_b = text_b.split()

    max_possible = min(len(words_a), len(words_b))
    for overlap_len in range(max_possible, 0, -1):
        if words_a[-overlap_len:] == words_b[:overlap_len]:
            return overlap_len
    return 0


# ── Property 10 ───────────────────────────────────────────────────────────────

@given(st.text(min_size=1, max_size=10000))
@settings(max_examples=100)
def test_property_10_chunk_word_limit_and_overlap_invariant(text: str):
    """
    **Validates: Requirements 4.1, 4.2**

    Property 10: Chunk Word Limit and Overlap Invariant
    - Every chunk produced by the chunker has word count ≤ 500.
    - For every consecutive pair of chunks from the same segment the shared
      word overlap is between 45 and 55 words inclusive.
    """
    segment = TextSegment(text=text)
    chunks = chunk_segments([segment], document_id="doc-prop10", file_type=FileType.TXT)

    for chunk in chunks:
        wc = _word_count(chunk.text)
        assert wc <= 500, (
            f"Chunk exceeds 500 words: {wc} words. "
            f"Chunk text (first 200 chars): {chunk.text[:200]!r}"
        )

    # Check overlap between consecutive chunks
    # Overlap only applies when more than one chunk was produced
    if len(chunks) > 1:
        for i in range(len(chunks) - 1):
            overlap = _overlap_word_count(chunks[i].text, chunks[i + 1].text)
            assert 45 <= overlap <= 55, (
                f"Overlap between chunk {i} and chunk {i+1} is {overlap} words "
                f"(expected 45–55). "
                f"Chunk {i} ends: {chunks[i].text.split()[-60:]!r}. "
                f"Chunk {i+1} starts: {chunks[i+1].text.split()[:60:]!r}."
            )


# ── Property 11 ───────────────────────────────────────────────────────────────

@given(
    document_id=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_",
        ),
    ),
    file_type=st.sampled_from(FileType),
    location=st.one_of(st.none(), st.integers(min_value=1, max_value=1000)),
    text=st.text(min_size=1, max_size=5000),
)
@settings(max_examples=100)
def test_property_11_chunk_metadata_attachment(
    document_id: str,
    file_type: FileType,
    location,
    text: str,
):
    """
    **Validates: Requirements 4.5, 5.3, 10.1**

    Property 11: Chunker Attaches Complete Metadata to Every Chunk
    - Every emitted chunk has chunk.document_id == document_id.
    - Every emitted chunk has chunk.file_type == file_type.
    - Every emitted chunk has chunk.location == location (including None when
      location is absent on the source segment).
    """
    segment = TextSegment(text=text, location=location)
    chunks = chunk_segments([segment], document_id=document_id, file_type=file_type)

    for chunk in chunks:
        assert chunk.document_id == document_id, (
            f"Expected document_id={document_id!r}, got {chunk.document_id!r}"
        )
        assert chunk.file_type == file_type, (
            f"Expected file_type={file_type!r}, got {chunk.file_type!r}"
        )
        assert chunk.location == location, (
            f"Expected location={location!r}, got {chunk.location!r}"
        )
