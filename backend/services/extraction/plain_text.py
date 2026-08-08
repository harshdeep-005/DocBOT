"""
services/extraction/plain_text.py — Plain Text / Markdown Extractor stub.

Full implementation is handled in a later task. This stub defines the
correct function signature so that router.py is importable and testable.
"""

from typing import List

from models.schemas import TextSegment


def extract_plain_text(file_bytes: bytes) -> List[TextSegment]:
    """
    Extract text from a plain-text or Markdown file.

    Decodes the bytes as UTF-8 and returns a single TextSegment with no
    `location` field (location is absent, not null).

    Args:
        file_bytes: Raw bytes of the TXT or MD file.

    Returns:
        A list containing exactly one TextSegment with no location.
    """
    decoded_text = file_bytes.decode("utf-8")
    return [TextSegment(text=decoded_text)]
