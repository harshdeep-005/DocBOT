# Implementation Plan: RAG Document Chatbot

## Overview

Implement a full-stack RAG chatbot with a FastAPI Python backend and a Next.js + Tailwind CSS frontend. The backend orchestrates file type detection, text extraction (PDF/DOCX/PPTX/TXT/MD), chunking, Gemini-powered embedding, Chroma vector storage, similarity retrieval, and answer generation. The frontend provides a file upload zone, a chat window, and a collapsible sources panel. All 24 correctness properties are covered by Hypothesis (backend) and fast-check (frontend) property-based tests.

---

## Tasks

- [x] 1. Project scaffolding and environment setup
  - [x] 1.1 Scaffold backend directory structure and install dependencies
    - Create `backend/` with `routes/`, `services/extraction/`, `models/`, `tests/` directories
    - Create `backend/requirements.txt` pinning: `fastapi`, `uvicorn[standard]`, `python-multipart`, `pydantic`, `pymupdf`, `python-docx`, `python-pptx`, `chromadb`, `google-generativeai`, `python-magic`, `pytest`, `pytest-asyncio`, `httpx`, `hypothesis`
    - Create `backend/main.py` with FastAPI app instantiation, router registration, and GEMINI_API_KEY startup guard (log CRITICAL and `sys.exit(1)` when absent/empty)
    - Create `backend/.env.example` with `GEMINI_API_KEY` and `TOP_K_CHUNKS` placeholder entries
    - _Requirements: 5.2, 5.8, 9.1, 9.2, 9.3_

  - [x] 1.2 Scaffold frontend directory structure and install dependencies
    - Bootstrap Next.js app in `frontend/` with TypeScript and Tailwind CSS
    - Install `jest`, `@testing-library/react`, `@testing-library/jest-dom`, `fast-check`, `ts-jest`
    - Create `frontend/.env.local.example` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
    - _Requirements: 9.4, 9.5_

  - [x] 1.3 Add .gitignore entries for secrets and environment files
    - Add `.env`, `.env.local`, `*.pyc`, `__pycache__/`, `.chroma/`, `node_modules/`, `.next/` to root `.gitignore`
    - _Requirements: 9.6_

- [x] 2. Backend data models and shared schemas
  - [x] 2.1 Implement `models/schemas.py` with all Pydantic models
    - Define `FileType` enum (pdf, docx, pptx, txt, md)
    - Define `TextSegment`, `Chunk`, `Citation`, `UploadResponse`, `AskRequest`, `SourceChunk`, `AskResponse`
    - Enforce `AskRequest.question` `min_length=1`, `max_length=2000`
    - _Requirements: 1.3, 4.5, 5.3, 6.2, 7.1_

  - [x] 2.2 Write unit tests for schema validation edge cases
    - Test `AskRequest` rejects empty string and strings > 2000 chars
    - Test `Chunk` with and without `location` field
    - _Requirements: 6.9_


- [x] 3. File type detection and routing
  - [x] 3.1 Implement `services/extraction/router.py`
    - Detect file type using magic bytes first (`%PDF`, ZIP+content-type.xml for DOCX, ZIP+ppt/ for PPTX)
    - Fall back to declared MIME type; use `.md` extension as tiebreaker when MIME is `text/plain`
    - Raise `UnsupportedTypeError` (→ HTTP 415) for unrecognised types
    - Raise `UnreadableFileError` (→ HTTP 422) when the file header cannot be read
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 3.2 Write property test for magic-bytes-first detection (Property 4)
    - **Property 4: Magic-Bytes-First Type Detection**
    - **Validates: Requirements 2.1**
    - Generate files whose magic bytes indicate format X but whose extension/MIME indicates format Y; assert routing is always to X's extractor

  - [x] 3.3 Write property test for unsupported type → HTTP 415 (Property 5)
    - **Property 5: Unsupported Type Returns HTTP 415**
    - **Validates: Requirements 2.6**
    - Generate random byte sequences that match no supported magic bytes and no supported MIME type; assert HTTP 415 response with message naming type and listing accepted types

  - [x] 3.4 Write unit tests for file type detection
    - One representative test per supported type (PDF, DOCX, PPTX, TXT, MD)
    - Test corrupt header → HTTP 422
    - Test unsupported type that also exceeds 50 MB → HTTP 415 (type checked first)
    - _Requirements: 1.4, 2.1–2.7_


- [x] 4. Text extractors
  - [x] 4.1 Implement `services/extraction/pdf.py` — PDF Extractor
    - Use PyMuPDF (`fitz`) to extract text per page
    - Emit segments with 1-based page `location`
    - Skip pages with fewer than 50 extractable characters and log a warning with the page number
    - _Requirements: 3.1, 3.2_

  - [ ]* 4.2 Write property test for PDF page locations (Property 6)
    - **Property 6: PDF Extraction Produces Correct 1-Based Page Locations**
    - **Validates: Requirements 3.1**
    - Generate synthetic multi-page PDF bytes; assert exactly N segments with locations 1…N for N text-extractable pages

  - [x] 4.3 Implement `services/extraction/docx.py` — DOCX Extractor
    - Use python-docx to extract text per paragraph
    - Assign `location = ceil(paragraph_index / 10)` where `paragraph_index` is 1-based
    - _Requirements: 3.3_

  - [ ]* 4.4 Write property test for DOCX paragraph locations (Property 7)
    - **Property 7: DOCX Extraction Applies the ceil(paragraph_index / 10) Formula**
    - **Validates: Requirements 3.3**
    - Generate synthetic DOCX with N paragraphs; assert each segment's location equals ⌈paragraph_index / 10⌉

  - [x] 4.5 Implement `services/extraction/pptx.py` — PPTX Extractor
    - Use python-pptx to extract text per slide
    - Assign `location` = 1-based slide number
    - _Requirements: 3.4_

  - [ ]* 4.6 Write property test for PPTX slide locations (Property 8)
    - **Property 8: PPTX Extraction Produces Correct 1-Based Slide Locations**
    - **Validates: Requirements 3.4**
    - Generate synthetic PPTX with N slides; assert each segment's location equals its 1-based slide number

  - [x] 4.7 Implement `services/extraction/plain_text.py` — Plain Text Extractor
    - Decode bytes as UTF-8; return a single `TextSegment` with no `location` field
    - _Requirements: 3.5_

  - [ ]* 4.8 Write property test for TXT/MD no-location extraction (Property 9)
    - **Property 9: TXT/MD Extraction Produces a Single Segment with No Location**
    - **Validates: Requirements 3.5, 10.1**
    - Use `st.text()` to generate arbitrary content; assert exactly one segment whose `location` attribute is absent (not null, not zero)

  - [x] 4.9 Write unit tests for all extractors
    - Test scanned-page skipping: PDF with near-empty page alongside a normal page
    - Test unhandled extraction exception → HTTP 500 with filename and exception type
    - _Requirements: 3.2, 3.6_


- [x] 5. Text chunker
  - [x] 5.1 Implement `services/chunking.py` — Chunker
    - Split segments at paragraph boundaries (blank-line delimited); ≤ 500 words per chunk
    - Apply 45–55 word overlap between consecutive chunks from the same source segment
    - Fall back to sentence-boundary split when a single paragraph exceeds 500 words
    - Treat segments shorter than 500 words as a single chunk
    - Attach `document_id`, `file_type`, and `location` (when present) to every `Chunk`; assign `chunk_id` as UUID4
    - Log a warning (with `document_id` and 1-based segment index) for empty/whitespace segments; skip them without emitting a chunk
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 5.2 Write property test for chunk word limit and overlap invariant (Property 10)
    - **Property 10: Chunk Word Limit and Overlap Invariant**
    - **Validates: Requirements 4.1, 4.2**
    - Use `st.text(min_size=1, max_size=10000)` to generate arbitrary text; assert `word_count(chunk.text) ≤ 500` for every chunk AND shared overlap between consecutive same-segment chunks is 45–55 words inclusive

  - [x] 5.3 Write property test for chunk metadata attachment (Property 11)
    - **Property 11: Chunker Attaches Complete Metadata to Every Chunk**
    - **Validates: Requirements 4.5, 5.3, 10.1**
    - Generate segments with arbitrary `document_id`, `file_type`, and optional `location`; assert every emitted chunk carries `document_id` and `file_type` identical to inputs and mirrors the segment's `location` (or absence thereof)

  - [ ]* 5.4 Write property test for chunker idempotence (Property 24)
    - **Property 24: Chunker Idempotence**
    - **Validates: Requirements 10.3**
    - Generate any valid segment list with fixed `document_id` and `file_type`; run chunker twice; assert chunk counts, texts, metadata, and order are identical in both runs

  - [x] 5.5 Write unit tests for the chunker
    - Short segment (< 500 words) → exactly one chunk, no splitting
    - Empty/whitespace segment → warning logged, no chunk emitted, processing continues
    - Oversized single paragraph → split at sentence boundary, all chunks ≤ 500 words
    - _Requirements: 4.3, 4.4, 4.6_


- [x] 6. Embedder
  - [x] 6.1 Implement `services/embeddings.py` — Embedder
    - Read `GEMINI_API_KEY` from environment; raise `GeminiAPIError` (→ HTTP 502) if absent/empty at invocation time
    - Implement `embed_texts(texts: List[str]) -> List[List[float]]` calling the Gemini embedding model once per text
    - Implement `embed_single(text: str) -> List[float]` as a convenience wrapper
    - _Requirements: 5.1, 5.2_

  - [x] 6.2 Write property test for embedder call count (Property 12)
    - **Property 12: Embedder Is Called Exactly Once per Chunk**
    - **Validates: Requirements 5.1**
    - Use `st.lists(st.text(), min_size=1)` to generate chunk lists of varying length N; mock the Gemini client and assert the API was called exactly N times

  - [x] 6.3 Write unit tests for the embedder
    - Gemini API error mid-ingestion → raises `GeminiAPIError` with chunk index and reason
    - `GEMINI_API_KEY` absent at invocation → HTTP 500 with configured message
    - _Requirements: 5.2, 5.5_


- [x] 7. Vector store
  - [x] 7.1 Implement `services/vector_store.py` — Vector Store (Chroma)
    - Implement `replace_document_chunks(document_id, chunks, embeddings)`: delete all existing records for `document_id`, then bulk-insert new records in a single `collection.add()` call; raise `VectorStoreError` on write failure
    - Implement `similarity_search(document_id, query_embedding, top_k)`: return top-k chunks scoped to `document_id`; return empty list when no chunks exist
    - Implement `rollback_document(document_id)`: best-effort delete of all chunks for `document_id`; catch and log Chroma errors without re-raising
    - Omit `location` key from Chroma metadata entirely for TXT/MD chunks (do not store `null` or empty string)
    - _Requirements: 5.3, 5.4, 5.7, 10.1, 10.2_

  - [x] 7.2 Write property test for chunk metadata round-trip fidelity (Property 13)
    - **Property 13: Chunk Metadata Round-Trip Fidelity**
    - **Validates: Requirements 5.3, 10.1**
    - Generate `Chunk` objects with arbitrary `document_id`, `file_type`, `text`, and optional `location`; store then retrieve; assert every field is byte-for-byte identical and TXT/MD chunks have no `location` key in the retrieved record

  - [x] 7.3 Write property test for atomic replacement (Property 14)
    - **Property 14: Atomic Replacement — Post-Ingestion Query Reflects Only New Chunks**
    - **Validates: Requirements 5.4**
    - Generate two successive chunk sets for the same `document_id`; after the second ingestion completes, perform a similarity search and assert no chunk from the first set appears in results

  - [x] 7.4 Write property test for retrieval scoped to document_id (Property 16)
    - **Property 16: Retrieval Is Scoped to the Queried Document_ID**
    - **Validates: Requirements 6.4, 10.2**
    - Store chunks for multiple `document_id` values simultaneously; for each query, assert every returned chunk carries the exact queried `document_id`

  - [x] 7.5 Write unit tests for the vector store
    - Vector store write error → rollback attempted + HTTP 500 with storage-failure message
    - Rollback failure does not suppress the original HTTP 500/502 response
    - Similarity search with no matching document_id → empty list returned
    - _Requirements: 5.4, 5.5, 5.7_


- [x] 8. Answer generator
  - [x] 8.1 Implement `services/generation.py` — Generator
    - Implement `build_prompt(question, chunks)`: embed chunk texts into the template that instructs the LLM to answer only from context and to use the exact "not found" phrase when the answer is absent
    - Implement `generate_answer(question, chunks)`: call the Gemini LLM with the constructed prompt; raise `GeminiAPIError` on failure
    - _Requirements: 6.5, 6.7_

  - [x] 8.2 Write property test for grounded prompt anti-hallucination instruction (Property 17)
    - **Property 17: Grounded Prompt Always Contains the Anti-Hallucination Instruction**
    - **Validates: Requirements 6.5**
    - Use `st.text()` × `st.lists(chunk strategy)` to generate arbitrary question + chunk combinations; assert every prompt contains both the "answer only from context" instruction and the exact "not found" fallback phrase

  - [x] 8.3 Write unit tests for the generator
    - LLM returns "not found" phrase → answer field is the fixed "The answer was not found in the uploaded document."
    - Gemini API error during generation → raises `GeminiAPIError` with identifying message
    - _Requirements: 6.7, 6.8_


- [x] 9. Backend upload route
  - [x] 9.1 Implement `routes/upload.py` — POST /upload
    - Validate file size ≤ 50 MB (HTTP 422 if exceeded), then validate page/slide count ≤ 300 (HTTP 422 if exceeded)
    - Check file type first; return HTTP 415 before evaluating size when type is unsupported
    - Generate UUID4 `document_id`
    - Orchestrate: detect type → extract → chunk → embed → vector store (with rollback on embed or write failure)
    - Return HTTP 200 `{ document_id, chunk_count }` on success
    - _Requirements: 1.3, 1.4, 1.5, 3.6, 5.5, 5.6, 5.7_

  - [ ]* 9.2 Write property test for document_id uniqueness (Property 1)
    - **Property 1: Document_ID Uniqueness**
    - **Validates: Requirements 1.3**
    - Use `st.binary()` to generate valid file bytes; POST two independent uploads and assert the returned `document_id` values are distinct non-empty strings

  - [ ]* 9.3 Write property test for file size and page limit rejection (Property 2)
    - **Property 2: File Size and Page Limit Rejection**
    - **Validates: Requirements 1.5**
    - Generate files whose byte count exceeds 50 MB or page/slide count exceeds 300; assert HTTP 422 with a message identifying which limit was exceeded

  - [ ]* 9.4 Write property test for successful ingestion chunk_count (Property 15)
    - **Property 15: Successful Ingestion Response Matches Actual Stored Count**
    - **Validates: Requirements 5.6**
    - Upload valid documents of varying length; assert the `chunk_count` in the HTTP 200 body equals the number of chunks actually inserted into the vector store

  - [ ]* 9.5 Write unit tests for the upload route
    - Gemini embedding API error mid-ingestion → rollback + HTTP 502 with chunk index and reason
    - Vector store write error → rollback + HTTP 500 with storage-failure message
    - Corrupt file header → HTTP 422
    - Unsupported type that also exceeds 50 MB → HTTP 415 (type checked first)
    - _Requirements: 1.4, 1.5, 5.5, 5.7_


- [x] 10. Backend ask route
  - [x] 10.1 Implement `routes/ask.py` — POST /ask
    - Validate question is non-empty and ≤ 2000 characters; return HTTP 422 without calling any AI API if invalid
    - Embed question → similarity search scoped to `document_id` (top-k from `TOP_K_CHUNKS` env var, default 5, range 1–20)
    - Build deduplicated `citations` list (dedup key = `location`; format "Page N" for PDF/DOCX, "Slide N" for PPTX)
    - Return "not found" fixed phrase when no chunks found or LLM response contains the "not found" phrase
    - Return HTTP 502 on Gemini embedding or LLM failure, identifying which call failed
    - Return HTTP 200 `{ answer, citations, chunks }` on success
    - _Requirements: 6.2–6.8, 7.1_

  - [ ]* 10.2 Write property test for invalid question → HTTP 422 without AI calls (Property 18)
    - **Property 18: Invalid Question Length Returns HTTP 422 Without AI Calls**
    - **Validates: Requirements 6.9**
    - Generate question strings of length 0 or > 2000; assert HTTP 422 response and zero calls to Gemini APIs

  - [ ]* 10.3 Write property test for citation deduplication and format (Property 19)
    - **Property 19: Citations Are Deduplicated by Location and Correctly Formatted**
    - **Validates: Requirements 7.1**
    - Generate lists of chunks with varied `location` values and `file_type` values; assert the citation list has at most one entry per unique location, formatted as "Page N" (PDF/DOCX) or "Slide N" (PPTX)

  - [ ]* 10.4 Write unit tests for the ask route
    - Empty question → HTTP 422 with configured message, no AI calls
    - Question > 2000 chars → HTTP 422 with configured message, no AI calls
    - No chunks found for document_id → "not found" answer + HTTP 200
    - LLM returns "not found" phrase → answer field is the exact fixed phrase
    - Gemini embedding API failure → HTTP 502 naming the failing call
    - Gemini LLM API failure → HTTP 502 naming the failing call
    - _Requirements: 6.7, 6.8, 6.9_

- [x] 11. Backend configuration and startup guard
  - [x] 11.1 Implement `TOP_K_CHUNKS` env-var reading with fallback
    - Read `TOP_K_CHUNKS` from environment at startup; fall back to `5` when absent, non-numeric, or outside range 1–20
    - _Requirements: 9.2_

  - [ ]* 11.2 Write property test for TOP_K_CHUNKS default fallback (Property 23)
    - **Property 23: TOP_K_CHUNKS Defaults to 5 for Any Invalid Configuration**
    - **Validates: Requirements 9.2**
    - Generate absent, non-numeric, and out-of-range values for `TOP_K_CHUNKS`; assert the resolved value is exactly 5

  - [ ]* 11.3 Write unit test for GEMINI_API_KEY absent at startup
    - Assert the server refuses to start and logs `CRITICAL: GEMINI_API_KEY is not set`
    - _Requirements: 5.8, 9.1_


- [x] 12. Checkpoint — Backend complete
  - Ensure all backend tests pass. Ask the user if any questions arise before proceeding to the frontend.

- [x] 13. Frontend API client
  - [x] 13.1 Implement `frontend/lib/api.ts`
    - Define `API_BASE` reading `NEXT_PUBLIC_API_URL` with fallback to `http://localhost:8000`; log a build-time warning when the variable is absent
    - Implement `uploadDocument(file: File): Promise<UploadResponse>` with a 30-second `AbortController` timeout
    - Implement `askQuestion(question: string, documentId: string): Promise<AskResponse>` with a 30-second `AbortController` timeout
    - Both functions throw `ApiError` (with a user-friendly message) on any non-2xx response or network failure; never surface HTTP status codes or stack traces
    - Export all TypeScript types: `UploadResponse`, `Citation`, `SourceChunk`, `AskResponse`, `Message`
    - _Requirements: 1.2, 6.2, 8.4, 9.4_

  - [x] 13.2 Write unit tests for `lib/api.ts`
    - `NEXT_PUBLIC_API_URL` absent → fallback to `http://localhost:8000`
    - Non-2xx response → `ApiError` thrown with user-friendly message (no raw status code exposed)
    - Request exceeds 30 seconds → timeout throws `ApiError` with timeout message
    - _Requirements: 8.4, 9.4_


- [x] 14. UploadBox component
  - [x] 14.1 Implement `frontend/components/UploadBox.tsx`
    - Render a file `<input>` with `accept=".pdf,.docx,.pptx,.txt,.md"`
    - Manage state: `file`, `uploading`, `error`, `documentId`
    - On success: call `onUploadSuccess(documentId)` callback and clear error
    - On failure or 30-second timeout: set persistent inline `error`; never retry automatically
    - On new upload attempt: clear previous error
    - Display error inline adjacent to the upload zone (no toasts)
    - _Requirements: 1.1, 1.6, 8.1, 8.2, 8.3, 8.5_

  - [x] 14.2 Write property test for upload clearing prior state (Property 3)
    - **Property 3: Successful Upload Clears Prior State**
    - **Validates: Requirements 1.7**
    - Use fast-check to generate arbitrary prior frontend state (existing `documentId`, non-empty `messages` array); simulate a successful upload; assert `documentId` is replaced and `messages` is reset to empty

  - [x] 14.3 Write property test for inline errors in correct zone (Property 21)
    - **Property 21: Inline Errors Appear in the Correct Zone and Persist**
    - **Validates: Requirements 8.1, 8.3**
    - Generate 4xx and 5xx responses from the upload endpoint; assert a non-technical persistent inline error appears inside `UploadBox`; simulate a subsequent successful upload and assert the error is gone

  - [x] 14.4 Write property test for controls enabled during error state (Property 22)
    - **Property 22: Controls Remain Enabled During Error State**
    - **Validates: Requirements 8.5**
    - Generate upload error states; assert file input and upload submit control are `enabled` (not `disabled`)

  - [x] 14.5 Write unit tests for UploadBox
    - `accept` attribute contains all five extensions (`.pdf`, `.docx`, `.pptx`, `.txt`, `.md`)
    - No toast notification rendered on error
    - Error message persists until next successful upload
    - _Requirements: 1.1, 1.6, 8.2_


- [x] 15. ChatWindow component
  - [x] 15.1 Implement `frontend/components/ChatWindow.tsx`
    - Manage state: `messages`, `question`, `loading`, `error`
    - Disable question `<input>` and submit control when `documentId` is `null`; display "Upload a document to start chatting" label
    - On question submit: call `askQuestion`; append `{ role: "user", text: question }` immediately; append `{ role: "assistant", text: answer, citations, chunks }` on response
    - Render citations immediately below each assistant answer text, before any other UI elements
    - Display persistent inline `error` below the message list on 4xx/5xx or timeout; clear on next successful question
    - _Requirements: 6.1, 6.2, 7.2, 8.1, 8.2, 8.3, 8.5_

  - [x]* 15.2 Write property test for inline errors in correct zone — chat variant (Property 21 chat path)
    - **Property 21 (chat path): Inline Errors Appear in the Correct Zone and Persist**
    - **Validates: Requirements 8.1, 8.3**
    - Generate 4xx/5xx responses from the ask endpoint; assert inline error appears inside `ChatWindow`; simulate a successful question and assert the error clears

  - [ ]* 15.3 Write property test for controls enabled during error — chat variant (Property 22 chat path)
    - **Property 22 (chat path): Controls Remain Enabled During Error State**
    - **Validates: Requirements 8.5**
    - Generate ask error states; assert question input and submit control are `enabled`

  - [ ]* 15.4 Write unit tests for ChatWindow
    - Question input and submit disabled when `documentId` is null with visible label
    - Citations rendered immediately below answer text in same message bubble
    - No toast notification on error
    - _Requirements: 6.1, 7.2, 8.2_


- [x] 16. SourcesPanel component
  - [x] 16.1 Implement `frontend/components/SourcesPanel.tsx`
    - Accept `chunks: SourceChunk[]` and render collapsed by default (`defaultCollapsed: true`)
    - For each chunk: render rank label ("Source 1", "Source 2", …), citation label ("Page N" / "Slide N") when `citation` is present, and the full chunk text
    - Omit the citation label entirely when `citation` is absent (TXT/MD source); no placeholder or null value
    - If any element is missing for a chunk, still render the chunk with available elements
    - _Requirements: 7.3, 7.4, 7.5_

  - [ ]* 16.2 Write property test for source chunk rendering (Property 20)
    - **Property 20: Source Chunk Rendering Includes All Available Elements**
    - **Validates: Requirements 7.3, 7.4**
    - Use fast-check to generate `SourceChunk` objects with and without `citation`; assert rank label and full text always appear; assert citation label present when `citation` exists and absent (no placeholder) when it does not

  - [x] 16.3 Write unit tests for SourcesPanel
    - Panel is collapsed by default; can be expanded on demand
    - TXT/MD chunk renders without any citation label or placeholder
    - _Requirements: 7.4, 7.5_

- [x] 17. Main page wiring
  - [x] 17.1 Implement `frontend/app/page.tsx` (or `pages/index.tsx`)
    - Compose `UploadBox`, `ChatWindow`, and `SourcesPanel` on the main page
    - Lift `documentId` and latest `chunks` state; pass `documentId` to `ChatWindow` and latest `chunks` to `SourcesPanel`
    - On `onUploadSuccess`: update `documentId` and clear conversation history
    - Apply Tailwind layout (responsive two-column or stacked)
    - _Requirements: 1.7, 6.1, 7.5_

  - [x] 17.2 Write unit tests for main page composition
    - New upload success resets conversation history and updates `documentId`
    - `SourcesPanel` receives the chunks from the latest answer
    - _Requirements: 1.7_


- [x] 18. Checkpoint — Frontend complete
  - Ensure all frontend tests pass. Ask the user if any questions arise before proceeding to integration tests.

- [x] 19. Integration tests
  - [x] 19.1 Write backend integration tests (mocked at network boundary)
    - Upload a real PDF → assert non-empty `document_id` and `chunk_count > 0`; query a question → assert non-empty answer with "Page N" citations
    - Upload a PPTX → assert citations use "Slide N" format
    - Upload a TXT file → assert answer has no citation labels
    - Re-upload to the same session → assert prior conversation state is cleared on the frontend
    - _Requirements: 1.7, 3.1, 3.4, 3.5, 7.1_

  - [x] 19.2 Configure test infrastructure
    - Create `backend/tests/conftest.py` with pytest fixtures: `test_client` (httpx ASGI client), `mock_gemini` (patches `google-generativeai` calls), `test_env` (sets `GEMINI_API_KEY=test-key`, `TOP_K_CHUNKS=5`)
    - Create `frontend/jest.config.ts` with `ts-jest` transformer, `@testing-library/jest-dom` setup, and fast-check configured for 100 iterations
    - _Requirements: (test infrastructure)_

- [x] 20. README
  - [x] 20.1 Write `README.md` at the project root
    - Document prerequisites, local setup steps (clone → install backend deps → install frontend deps → copy `.env.example` → run backend → run frontend), and how to run tests (`pytest` for backend, `jest` for frontend)
    - List all supported file types and key environment variables
    - _Requirements: 9.3, 9.5_

- [x] 21. Final checkpoint — All tests pass
  - Ensure all property-based, unit, and integration tests pass. Ask the user if any questions arise.


---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; all property and unit tests must pass before merge per the design's CI policy.
- Each task references specific requirements for traceability.
- Checkpoints (tasks 12, 18, 21) gate progress between major milestones.
- Property tests use Hypothesis (`@settings(max_examples=100)`) for backend and fast-check for frontend, mirroring the design's testing strategy.
- Unit tests use `pytest` + `httpx` ASGI client for backend routes; `jest` + `@testing-library/react` for frontend components.
- All Gemini API calls are mocked at the `google-generativeai` / network boundary in unit and property tests; integration tests use real Gemini API calls with a live key.
- The `.env.test` file should set `GEMINI_API_KEY=test-key` and `TOP_K_CHUNKS=5` for the test environment.
- Never hardcode credentials; always read from environment variables.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "19.2"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4", "4.1", "4.3", "4.5", "4.7"] },
    { "id": 4, "tasks": ["4.2", "4.4", "4.6", "4.8", "4.9", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "5.5", "6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3", "7.1"] },
    { "id": 7, "tasks": ["7.2", "7.3", "7.4", "7.5", "8.1"] },
    { "id": 8, "tasks": ["8.2", "8.3", "11.1"] },
    { "id": 9, "tasks": ["9.1", "11.2", "11.3"] },
    { "id": 10, "tasks": ["9.2", "9.3", "9.4", "9.5", "10.1"] },
    { "id": 11, "tasks": ["10.2", "10.3", "10.4"] },
    { "id": 12, "tasks": ["13.1"] },
    { "id": 13, "tasks": ["13.2", "14.1"] },
    { "id": 14, "tasks": ["14.2", "14.3", "14.4", "14.5", "15.1"] },
    { "id": 15, "tasks": ["15.2", "15.3", "15.4", "16.1"] },
    { "id": 16, "tasks": ["16.2", "16.3", "17.1"] },
    { "id": 17, "tasks": ["17.2"] },
    { "id": 18, "tasks": ["19.1", "20.1"] }
  ]
}
```
