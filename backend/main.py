"""
main.py — FastAPI application entry point for the RAG Document Chatbot backend.

Startup guard: refuses to start when GEMINI_API_KEY is absent or empty,
logging a CRITICAL message and exiting with code 1 (Requirements 5.8, 9.1).
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load .env from the backend directory (or project root as fallback)
load_dotenv(Path(__file__).parent / ".env")
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Startup guard — GEMINI_API_KEY must be present before the app starts.
# Requirement 5.8 / 9.1: log CRITICAL and refuse to start when absent/empty.
# ---------------------------------------------------------------------------
_gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
if not _gemini_api_key:
    logger.critical(
        "GEMINI_API_KEY is not set. "
        "Set the GEMINI_API_KEY environment variable and restart the server."
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# FastAPI app instantiation
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RAG Document Chatbot API",
    description=(
        "Backend service for the RAG Document Chatbot. "
        "Supports document ingestion (PDF, DOCX, PPTX, TXT, Markdown) and "
        "natural-language question answering grounded in the uploaded document."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS middleware — allow all origins for local development.
# Tighten origins list before deploying to production.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router registration
# Routers are imported here once the route modules are implemented (tasks
# 9.1 and 10.1). The imports are guarded so that the scaffold compiles even
# before those modules exist.
# ---------------------------------------------------------------------------
try:
    from routes.upload import router as upload_router  # noqa: E402

    app.include_router(upload_router, prefix="/upload", tags=["upload"])
    logger.info("Upload router registered at POST /upload")
except ImportError:
    logger.warning(
        "routes/upload.py not yet implemented — /upload endpoint unavailable."
    )

try:
    from routes.ask import router as ask_router  # noqa: E402

    app.include_router(ask_router, prefix="/ask", tags=["ask"])
    logger.info("Ask router registered at POST /ask")
except ImportError:
    logger.warning(
        "routes/ask.py not yet implemented — /ask endpoint unavailable."
    )


# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Returns a simple liveness indicator."""
    return {"status": "ok"}
