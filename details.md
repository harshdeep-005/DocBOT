# RAG Document Chatbot — Interview Preparation Guide

Everything you built in this project, explained in depth for technical interviews.

---

## 1. What Is RAG?

**Retrieval-Augmented Generation (RAG)** is a pattern that grounds an LLM's answer in a specific knowledge source instead of relying on its training data.

**Pipeline:**
1. At upload time: extract text → chunk → embed → store vectors
2. At query time: embed question → similarity search → retrieve top-k chunks → pass to LLM with a strict "answer only from context" prompt

**Why RAG instead of just prompting the LLM?**
- LLMs hallucinate when asked about documents they haven't seen
- RAG gives the LLM only the relevant pieces at query time
- Answers are verifiable via citations (page numbers, slide numbers)
- Works with private documents without fine-tuning the model

---

## 2. Architecture Overview

```
Browser (Next.js)
    │
    ├── POST /upload  ──→  FastAPI
    │                        ├── File type detection (magic bytes)
    │                        ├── Text extraction (PyMuPDF / python-docx / python-pptx)
    │                        ├── Chunking (≤500 words, 45-55 word overlap)
    │                        ├── Embedding (Gemini gemini-embedding-2)
    │                        └── Storage (Chroma vector DB, persistent)
    │
    └── POST /ask     ──→  FastAPI
                             ├── Embed question (Gemini, retrieval_query task type)
                             ├── Similarity search (cosine, top-k=5 default)
                             ├── Build grounded prompt
                             ├── Generate answer (Gemini gemini-3.6-flash)
                             └── Return { answer, citations, chunks }
```

**Decoupled monorepo:** `/backend` (Python) and `/frontend` (TypeScript) communicate only over HTTP REST. No shared code, no shared database connection.

---

## 3. Backend Stack

### FastAPI
- **Version:** 0.111.0
- **Why FastAPI over Flask/Django?** Async-first, built-in Pydantic validation, automatic OpenAPI docs, type hints as contracts
- **ASGI server:** Uvicorn with `[standard]` extras (includes `watchfiles` for hot-reload, `httptools` for faster HTTP parsing)
- **Two routes:** `POST /upload` and `POST /ask`
- **CORS middleware:** configured for all origins (dev convenience; tighten in production)

### Pydantic v2
- All request/response schemas defined as Pydantic `BaseModel`
- `AskRequest.question` enforces `min_length=1, max_length=2000` at the model level
- `FileType` is a `str` enum (`pdf`, `docx`, `pptx`, `txt`, `md`)
- `Chunk` carries `chunk_id` (UUID4), `document_id`, `file_type`, `text`, and optional `location`

### File Type Detection
- **Magic bytes first** — never trust file extensions alone
  - PDF: `%PDF` header (`25 50 44 46`)
  - DOCX/PPTX: both are ZIP files (`50 4B 03 04`) — distinguished by checking internal ZIP entries (`word/` for DOCX, `ppt/` for PPTX)
  - TXT/MD: no magic bytes; falls back to MIME type + `.md` extension tiebreaker
- **Library:** `python-magic` 0.4.27 (wraps `libmagic`)

### Text Extractors
| Format | Library | Location metadata |
|--------|---------|-------------------|
| PDF | PyMuPDF (`fitz`) 1.24.3 | 1-based page number; pages with <50 chars (scanned) are skipped |
| DOCX | python-docx 1.1.2 | `ceil(paragraph_index / 10)` |
| PPTX | python-pptx 0.6.23 | 1-based slide number |
| TXT/MD | built-in `decode('utf-8')` | None (absent from metadata) |

### Text Chunking
- **Max chunk size:** 500 words
- **Overlap:** 45–55 words between consecutive chunks from the same segment
- **Split strategy:** paragraph boundaries first (blank-line delimited), sentence boundaries as fallback for oversized paragraphs
- **Sentence splitting:** regex `(?<=[.!?])(?:\s+|$)` — lookbehind to avoid splitting decimal numbers
- **Metadata attached to every chunk:** `document_id`, `file_type`, `location` (omitted for TXT/MD, never `null`)
- **Each chunk gets a UUID4** as `chunk_id`

### Embeddings
- **Model:** `models/gemini-embedding-2` (via `google-generativeai` 0.5.4)
- **Task types:** `retrieval_document` for chunks at ingestion time, `retrieval_query` for questions at query time — this is important for quality; same model, different task hints
- **Rate limit handling:** free tier = 100 req/min. Implemented batch-and-wait: batches of 80 with a 65-second pause between batches
- **API key:** read from `GEMINI_API_KEY` env var at invocation time (not import time) — fails gracefully with HTTP 502

### Vector Store (Chroma)
- **Version:** 0.5.0 (embedded, no separate server needed)
- **Client:** `chromadb.PersistentClient` — data survives server restarts (stored in `backend/.chroma/`)
- **Distance metric:** cosine similarity (`hnsw:space: cosine`)
- **HNSW index:** Chroma uses Hierarchical Navigable Small World graph for ANN (Approximate Nearest Neighbor) search
- **Scoping:** every chunk stores `document_id` in metadata; all queries use `where={"document_id": ...}` filter so users only retrieve from their uploaded document
- **Atomic replacement:** delete old chunks → bulk-insert new chunks in a single `collection.add()` call
- **Rollback:** best-effort `collection.delete()` on embedding/write failure; never re-raises

### Answer Generation
- **Model:** `gemini-3.6-flash`
- **Prompt template:** instructs the LLM to answer **only** from the provided context chunks and respond with an exact fixed phrase ("The answer was not found in the uploaded document.") when the answer is absent — prevents hallucination
- **"Not found" detection:** backend checks if LLM response contains the fixed phrase and normalises it

### Error Handling Pattern
| Condition | HTTP Status | Notes |
|-----------|-------------|-------|
| Unsupported file type | 415 | Checked before size limit |
| File >50 MB or >300 pages | 422 | |
| Corrupt file header | 422 | |
| Extraction error | 500 | Includes filename + exception type |
| Gemini embedding failure | 502 | Includes chunk index + reason; triggers rollback |
| Vector store write failure | 500 | Triggers rollback |
| Invalid question length | 422 | No AI API called |
| Gemini LLM failure | 502 | Identifies which call failed |

### Environment Variables
- `GEMINI_API_KEY` — required; server refuses to start without it (`sys.exit(1)`)
- `TOP_K_CHUNKS` — optional; default 5; range 1–20; falls back to 5 for invalid values
- `CHROMA_PERSIST_DIR` — optional; overrides Chroma storage path

---

## 4. Frontend Stack

### Next.js 15 (App Router)
- Uses the `app/` directory layout (`app/page.tsx`, `app/layout.tsx`)
- All interactive components are `"use client"` components (state, event handlers)
- `layout.tsx` injects Google Fonts via `<link>` and an inline FOUC-prevention script

### FOUC Prevention (Flash of Unstyled Content)
Problem: server renders `<html>` without `dark` class; FOUC-prevention script adds `dark` before React hydrates.
Solution: inline `<script>` in `<head>` reads `localStorage.theme` or `prefers-color-scheme` and adds `dark` class before first paint. `suppressHydrationWarning` on `<html>` tells React to ignore the class mismatch.

### Dark/Light Theme Toggle
- `ThemeToggle.tsx` uses a `MutationObserver` on `document.documentElement` to stay in sync with the DOM `class` attribute
- Persisted to `localStorage` as `"light"` or `"dark"`
- Icon: `wb_sunny` in light mode (shows current state), `light_mode` in dark mode

### CSS Architecture — CSS Custom Properties
All colors are defined as CSS variables in `globals.css` under `:root` (light) and `.dark` overrides:
- `--color-bg-page`, `--color-text-base`, `--color-primary`, `--color-teal`, etc.
- Semantic utility classes (`.t-base`, `.t-accent`, `.t-teal`, etc.) use `var()` so components never reference Tailwind color names directly
- **Benefit:** change the entire color scheme in one file

### Glassmorphism
- `.glass-panel`: `backdrop-filter: blur(12px)` + semi-transparent `rgba(255,255,255,0.85)` background + subtle border
- `.glass-input`: `backdrop-filter: blur(8px)` + nearly opaque white — gives a clear, defined input field
- Works in both light and dark modes via CSS variable overrides

### Tailwind CSS v4
- Uses `@tailwindcss/postcss` (not `tailwindcss/plugin` config file)
- Dark mode: `darkMode: 'class'` pattern
- `@plugin "@tailwindcss/typography"` for markdown rendering prose styles

### Markdown Rendering
- **Library:** `react-markdown`
- Assistant responses are rendered as rich markdown (headings, bold, code, lists, tables)
- Jest mock (`__mocks__/react-markdown.tsx`) renders plain text so tests work without parsing the ESM-only package

### Component Architecture
| Component | Responsibility |
|-----------|----------------|
| `page.tsx` | Lifts state: `documentId`, `docHistory`, `latestChunks`, `sidebarOpen` |
| `UploadBox` | File selection, upload form, exposes `triggerFilePicker()` via `forwardRef` + `useImperativeHandle` |
| `ChatWindow` | Message history, question input, calls `/ask`, renders markdown responses |
| `DocHistory` | List of uploaded docs; clicking switches active `documentId` without re-upload |
| `SourcesPanel` | Collapsible retrieved chunks with citations |
| `ThemeToggle` | Sun/moon button, persists to localStorage |

### `forwardRef` + `useImperativeHandle`
`UploadBox` exposes a `triggerFilePicker()` method so the sidebar button can open the browser's native file picker without having direct DOM access. This is the React pattern for imperative child actions from a parent.

### Document History (No Re-upload)
Each successful upload stores `{ documentId, filename, chunkCount, uploadedAt }` in React state. Selecting a previous doc just changes `documentId` — the chunks are already in Chroma's persistent store. The `ChatWindow` remounts via `key={documentId}` to reset conversation history.

### API Client (`lib/api.ts`)
- `uploadDocument()`: 10-minute timeout (large docs need batched embedding)
- `askQuestion()`: 30-second timeout
- Both use `AbortController` + `setTimeout` for timeouts
- All non-2xx responses throw `ApiError` with user-friendly messages — HTTP status codes are never surfaced to the UI
- `NEXT_PUBLIC_API_URL` read at build time; falls back to `http://localhost:8000` with a console warning

---

## 5. Testing Strategy

### Backend — Hypothesis (Property-Based Testing)
- **Library:** `hypothesis` 6.100.0
- Tests generate random inputs and assert properties hold universally (not just for hand-picked examples)
- Example: `test_chunk_word_limit` generates arbitrary text and asserts every chunk has ≤500 words across 100 random inputs

### Backend — pytest + httpx ASGI client
- `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` — tests the full FastAPI app without starting a server
- `conftest.py` fixture `isolate_vector_store` replaces the Chroma `PersistentClient` with an in-memory client per test so tests don't touch disk

### Frontend — Jest + React Testing Library
- `ts-jest` transforms TypeScript
- `jest-environment-jsdom` simulates a browser DOM
- `@testing-library/react` renders components and queries by accessible roles/labels

### Frontend — fast-check (Property-Based Testing)
- JavaScript equivalent of Hypothesis
- Used for properties like "successful upload always clears prior conversation history" — verified across 100 generated prior states

---

## 6. Key Design Decisions & Trade-offs

### Why Chroma (not Pinecone, Weaviate, pgvector)?
Chroma runs in-process with no external server. For a local demo app this means zero infrastructure setup. The trade-off is no horizontal scaling — fine for v1.

### Why not stream responses?
Streaming (Server-Sent Events or WebSockets) adds frontend complexity. The 30-second timeout is sufficient for the LLM response times at free tier. Listed as out-of-scope for v1.

### Why `retrieval_document` vs `retrieval_query` task types?
Gemini's embedding model is trained with task-specific signals. Using the right task type means document chunks and question embeddings are positioned in the same semantic space correctly — better retrieval accuracy.

### Why 45–55 word overlap?
Overlap ensures that answers that span a chunk boundary are still found. Too little overlap = missed answers; too much = redundant context sent to the LLM.

### Why magic-bytes-first file type detection?
Users can rename files. A `.pdf` extension on a DOCX file would silently fail extraction. Inspecting the actual bytes makes detection reliable.

### Why `sys.exit(1)` on missing API key at startup?
Failing fast at startup is better than failing on the first request with a cryptic 500 error. The operator knows immediately what's wrong.

### Why `forwardRef` for UploadBox?
The sidebar button needs to open the file picker. In React, DOM refs can't cross component boundaries without `forwardRef`. The `useImperativeHandle` hook exposes only the `triggerFilePicker` method — a narrow, intentional API surface.

---

## 7. Potential Interview Questions

**Q: What is cosine similarity and why use it for vector search?**
A: Cosine similarity measures the angle between two vectors, ignoring magnitude. It's the standard for semantic similarity because embedding vectors can have different magnitudes but represent similar meaning.

**Q: What happens when a user uploads the same document twice?**
A: The upload generates a new `document_id` (UUID4) each time. The old chunks remain in Chroma (scoped to the old ID). The UI switches to the new document. Document deduplication is out of scope for v1.

**Q: How does the grounded prompt prevent hallucination?**
A: The prompt explicitly instructs the LLM: "Answer using ONLY the context passages below. Do not use external knowledge. If the answer is not present, respond with exactly: [fixed phrase]." The backend then checks for that exact phrase in the response.

**Q: How do you handle scanned PDFs?**
A: Pages with fewer than 50 extractable characters are classified as scanned/image-based and skipped with a warning log. OCR is out of scope for v1.

**Q: Why does the vector store use `PersistentClient` instead of an in-memory client?**
A: An in-memory client loses all data on server restart. With `PersistentClient`, Chroma writes to `backend/.chroma/` on disk. This means uploaded documents survive server restarts and hot-reloads during development.

**Q: How did you handle the Gemini free-tier rate limit (100 req/min)?**
A: The embedder sends chunks in batches of 80 and pauses 65 seconds between batches. This keeps the per-minute rate well below 100.

**Q: What is the difference between a property-based test and a unit test?**
A: A unit test verifies a specific example. A property-based test generates hundreds of random inputs and verifies an invariant holds for all of them. Properties catch edge cases that hand-crafted examples miss.
