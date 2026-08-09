# DocBOT 

DocBOT is full-stack Retrieval-Augmented Generation (RAG) chatbot. Upload a document, ask natural-language questions, and get answers grounded exclusively in that document — complete with page/slide citations so you can verify every response.

**Stack:** FastAPI (Python) · Next.js + Tailwind CSS (TypeScript) · Chroma · Gemini API

---
### Demo

![DEMO](demo.gif)

### Screenshots

![File Upload](Screenshot%202026-08-09%20111745.png)

![Dark Mode](Screenshot%202026-08-09%20111842.png)

![Light Mode](Screenshot%202026-08-09%20111942.png)

---
## Supported File Types

| Format | Extension |
|---|---|
| PDF | `.pdf` |
| Word Document | `.docx` |
| PowerPoint | `.pptx` |
| Plain Text | `.txt` |
| Markdown | `.md` |

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- A **Gemini API key** — get one free at [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)

---

## Local Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd "PDF chatbot"
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd ../frontend
npm install
```

### 4. Configure environment variables

**Backend** — copy the example file and fill in your Gemini API key:

```bash
cd ../backend
cp .env.example .env
```

Open `backend/.env` and set your key:

```dotenv
GEMINI_API_KEY=your_actual_api_key_here
TOP_K_CHUNKS=5   # optional, default is 5
```

**Frontend** — copy the example file (the default points to `localhost:8000`, no changes needed for local dev):

```bash
cd ../frontend
cp .env.local.example .env.local
```

### 5. Start the backend

```bash
cd backend
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### 6. Start the frontend

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Running Tests

### Backend (pytest)

```bash
cd backend
pytest
```

### Frontend (Jest)

```bash
cd frontend
npm test
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | **Yes** | — | Gemini API key for embeddings and answer generation. Obtain from [aistudio.google.com/apikey](https://aistudio.google.com/apikey). The backend will refuse to start if this is missing. |
| `TOP_K_CHUNKS` | No | `5` | Number of document chunks retrieved per query. Must be an integer between 1 and 20 inclusive. |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Base URL of the running FastAPI backend. Change this if you deploy the backend to a remote host. |



