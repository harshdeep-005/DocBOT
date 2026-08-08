# RAG Document Chatbot — Project Spec

A chatbot that answers questions using the actual content of an uploaded document (PDF, DOCX, PPTX, TXT, or Markdown), using Retrieval-Augmented Generation (RAG). Answers are grounded in the document and include location citations (page/slide number where applicable) plus a view of the retrieved source chunks.

---

## 1. High-Level Architecture

**Ingestion path (when a document is uploaded):**

```
Upload Document (PDF, DOCX, PPTX, TXT, or MD)
    │
    ▼
Detect File Type
    │
    ├── PDF ──────────────────► Extract Text (per page, PyMuPDF)
    ├── DOCX ──────────────────► Extract Text (per paragraph, python-docx)
    ├── PPTX ──────────────────► Extract Text (per slide, python-pptx)
    └── TXT / MD ──────────────► Read Directly
    │
    ▼
Chunk Text (with page/slide number attached, where applicable)
    │
    ▼
Generate Embeddings (Gemini embedding model)
    │
    ▼
Store in Vector DB (Chroma) — embedding + text + location + doc id + file type
```

**Note on PDF text extraction:** if a PDF page returns little or no extractable text (i.e. it's a scanned/image page), it's skipped for v1 rather than OCR'd — OCR is listed as future work below. This keeps extraction simple and fast for the common case of native-text PDFs.

**Query path (when a user asks a question):**

```
User Question
    │
    ▼
Generate Question Embedding
    │
    ▼
Similarity Search in Vector DB (top 3-5 chunks)
    │
    ▼
Build Prompt (retrieved chunks + question + "answer only from context" instruction)
    │
    ▼
Gemini LLM generates answer
    │
    ▼
Return: answer + source pages + retrieved chunks
    │
    ▼
Frontend displays answer, citations, and a "view sources" panel
```

The backend is a stateless-ish API: it doesn't need to hold conversation memory for v1. Each `/ask` call is independent, scoped to one uploaded document.

---

## 2. Requirements

### Functional
- User can upload a document in PDF, DOCX, PPTX, TXT, or Markdown format
- System detects file type and routes to the correct extraction method
- System extracts and chunks the text, preserving page/slide numbers where applicable
- System generates embeddings for each chunk and stores them in a vector database
- User can ask a natural-language question about the uploaded document
- System retrieves the most relevant chunks via similarity search
- System generates an answer using only the retrieved context (no hallucinated content outside the document)
- Response includes location citations (page number for PDF/DOCX, slide number for PPTX)
- Response includes the raw retrieved chunks, viewable by the user
- If the answer isn't in the document, the system says so rather than guessing

### Non-Functional
- Single-document scope for v1 (no multi-PDF search, no user accounts)
- Reasonable response time for a demo (a few seconds per query is fine)
- Clear separation between backend (API) and frontend (UI) — no tight coupling
- API keys/secrets kept out of source control (`.env`, not committed)

### Out of Scope (v1)
- User authentication / accounts
- Multiple simultaneous documents / cross-document search
- Streaming responses
- OCR for scanned/image-based PDFs (see Future Work)

---

## 3. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| **Frontend** | React (Next.js) + Tailwind CSS | Upload UI + chat interface. Agent may suggest an alternative React setup if there's good reason, but stay in the React ecosystem. |
| **Backend** | FastAPI (Python) | REST API: `/upload`, `/ask`. Agent may suggest an alternative Python web framework if it has a clear justification. |
| **Database** | None required for v1 (no user/file metadata persistence needed) | If useful for tracking uploaded docs, SQLite is enough — no need for a full Postgres setup at this scale. |
| **Vector DB** | Chroma (embedded/local mode) | No external service to stand up — runs in-process, keeps setup fast. |
| **AI (LLM)** | Gemini API via Google AI Studio (free tier) | Used for answer generation. Model name should be pulled from current Google AI Studio docs at implementation time, not hardcoded from memory, since model names change. |
| **Embeddings** | Gemini embedding model (same API/key as above) | Keeps the whole AI layer on one provider/key for simplicity. |

**File extraction libraries:**
- PDF: PyMuPDF (`fitz`) — reliable, preserves page-level structure needed for citations
- DOCX: `python-docx`
- PPTX: `python-pptx`
- TXT / Markdown: read directly, no library needed

---

## 4. Basic Features (v1 scope)

1. **Upload document** — file picker or drag-and-drop, single file at a time; accepts PDF, DOCX, PPTX, TXT, Markdown
2. **Ask questions** — simple chat-style input against the uploaded document
3. **Grounded answers** — response generated only from retrieved document content
4. **Citations** — each answer shows which page/slide it came from
5. **View retrieved sources** — collapsible/expandable panel showing the actual chunks the model used to answer, so the user can verify the answer against the source text
6. **Graceful "not found"** — if the question can't be answered from the document, the system says so instead of fabricating an answer

---

## 5. Folder Structure

```
rag-document-chatbot/
├── backend/
│   ├── main.py                # FastAPI app, route definitions
│   ├── routes/
│   │   ├── upload.py          # POST /upload
│   │   └── ask.py             # POST /ask
│   ├── services/
│   │   ├── extraction/
│   │   │   ├── router.py      # Detects file type, dispatches to the right extractor
│   │   │   ├── pdf.py         # PyMuPDF text extraction
│   │   │   ├── docx.py        # python-docx extraction
│   │   │   ├── pptx.py        # python-pptx extraction
│   │   │   └── plain_text.py  # TXT / Markdown extraction
│   │   ├── chunking.py        # Text chunking logic
│   │   ├── embeddings.py      # Gemini embedding calls
│   │   ├── vector_store.py    # Chroma setup + similarity search
│   │   └── generation.py      # Prompt construction + Gemini LLM call
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response models
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── app/                   # Next.js app directory
│   │   ├── page.tsx           # Main chat/upload page
│   │   └── layout.tsx
│   ├── components/
│   │   ├── UploadBox.tsx
│   │   ├── ChatWindow.tsx
│   │   └── SourcesPanel.tsx
│   ├── lib/
│   │   └── api.ts             # Calls to backend endpoints
│   ├── package.json
│   └── .env.local.example
│
└── README.md
```

---

## 6. Setup Steps

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env            # add your GEMINI_API_KEY here
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL to backend address
npm run dev
```

### Verify
1. Open the frontend (typically `localhost:3000`)
2. Upload a text-based PDF, ask a question, confirm a page citation and retrieved chunks appear
3. Upload each other supported format (DOCX, PPTX, TXT, Markdown), confirm extraction and citation work correctly for each — note that PPTX citations reference slide number, not page number

---

# you may make any required change if you want