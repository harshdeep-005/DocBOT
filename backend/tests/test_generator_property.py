"""
tests/test_generator_property.py — Property-based tests for the Generator

Property 17: Grounded Prompt Always Contains the Anti-Hallucination Instruction

**Validates: Requirements 6.5**

For any arbitrary question string and any list of Chunk objects, the prompt
constructed by build_prompt must contain BOTH:
  1. The instruction to answer only from the provided context
  2. The exact "not found" fallback phrase:
     "The answer was not found in the uploaded document."
"""

import uuid

from hypothesis import given, settings
from hypothesis import strategies as st

from models.schemas import Chunk, FileType
from services.generation import (
    NOT_FOUND_PHRASE,
    build_prompt,
)

# ── Hypothesis strategies ────────────────────────────────────────────────────

# Strategy that generates valid FileType enum values
file_type_strategy = st.sampled_from(list(FileType))

# Strategy that generates a single Chunk with arbitrary text
chunk_strategy = st.builds(
    Chunk,
    chunk_id=st.uuids().map(str),
    document_id=st.uuids().map(str),
    file_type=file_type_strategy,
    text=st.text(min_size=1),          # non-empty chunk text
    location=st.one_of(st.none(), st.integers(min_value=1, max_value=300)),
)


# ── Property 17 ─────────────────────────────────────────────────────────────

@settings(max_examples=100)
@given(
    question=st.text(),
    chunks=st.lists(chunk_strategy, min_size=0, max_size=10),
)
def test_property_17_grounded_prompt_contains_anti_hallucination_instruction(
    question: str,
    chunks: list,
) -> None:
    """
    Property 17: For any question and any list of chunks, the prompt built by
    build_prompt must contain:
      1. The instruction to answer only from the provided context (the phrase
         "using ONLY" from the template header, which is the key phrase
         directing the LLM to use only the supplied context).
      2. The exact not-found fallback phrase.

    **Validates: Requirements 6.5**
    """
    prompt = build_prompt(question, chunks)

    # 1. The "answer only from context" instruction must be present.
    #    The template contains: "Answer the user's question using ONLY
    #    the context passages provided below. Do not use any external knowledge."
    assert "using ONLY" in prompt, (
        f"Prompt is missing the 'answer only from context' instruction.\n"
        f"Prompt:\n{prompt}"
    )

    # 2. The exact "not found" fallback phrase must be present.
    assert NOT_FOUND_PHRASE in prompt, (
        f"Prompt is missing the exact not-found fallback phrase.\n"
        f"Expected phrase: {NOT_FOUND_PHRASE!r}\n"
        f"Prompt:\n{prompt}"
    )
