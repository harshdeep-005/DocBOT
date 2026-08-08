# Requirements Document

## Introduction

A full-stack Retrieval-Augmented Generation (RAG) chatbot that lets users upload a single document (PDF, DOCX, PPTX, TXT, or Markdown) and ask natural-language questions about its contents. Answers are grounded exclusively in the uploaded document, include location citations (page number for PDF/DOCX, slide number for PPTX), and expose the retrieved source chunks so the user can verify every answer. The system is a local demo application with a Next.js frontend, a FastAPI backend, Chroma as the embedded vector store, and the Gemini API for both embeddings and answer generation.

---

## Glossary

- **System**: The RAG Document Chatbot application as a whole.
- **Backend**: The FastAPI Python service that handles upload, ingestion, and query requests.
- **Frontend**: The Next.js + Tailwind CSS web application the user interacts with.
- **Extractor**: The service component responsible for reading text out of an uploaded file.
- **Chunker**: The service component that splits extracted text into overlapping chunks suitable for embedding.
- **Chunk**: A unit of text (≤ 500 words, with ~50-word overlap) derived from the source document, carrying metadata (document ID, file type, location).
- **Embedder**: The service component that calls the Gemini embedding model to produce vector representations.
- **Vector_Store**: The Chroma embedded vector database that stores chunk embeddings and metadata.
- **Retriever**: The service component that performs similarity search in the Vector_Store.
- **Generator**: The service component that builds a grounded prompt and calls the Gemini LLM to produce an answer.
- **Document_ID**: A unique identifier assigned to an uploaded document on ingestion, used to scope all vector searches to that document.
- **Location**: The page number (PDF or DOCX) or slide number (PPTX) associated with a Chunk; absent for TXT/MD files.
- **TOP_K_CHUNKS**: Environment-configurable integer (default 5) controlling how many chunks the Retriever returns per query.
- **Scanned_Page**: A PDF page that yields fewer than a minimum threshold of extractable characters, indicating it is image-based rather than text-based.

---

## Requirements

### Requirement 1: Document Upload

**User Story:** As a user, I want to upload a single document file, so that I can ask questions about its contents.

#### Acceptance Criteria

1. THE Frontend SHALL provide a file input that accepts files with extensions `.pdf`, `.docx`, `.pptx`, `.txt`, and `.md`.
2. WHEN a user selects and submits a file, THE Frontend SHALL send it to the Backend via a `POST /upload` multipart request.
3. WHEN the Backend receives a `POST /upload` request, THE Backend SHALL assign a unique Document_ID to the uploaded file.
4. IF the detected file type of the upload is not one of PDF, DOCX, PPTX, TXT, or Markdown, THEN THE Backend SHALL return an HTTP 415 response with an error message that names the unsupported type and lists the accepted types. IF both the file type is unsupported AND the file exceeds 50 MB, THE Backend SHALL check file type first and return HTTP 415 without evaluating the size limit.
5. IF the uploaded document contains more than 300 pages or slides, OR IF the uploaded file exceeds 50 MB, THEN THE Backend SHALL reject the document with an HTTP 422 response containing a message that states which limit was exceeded.
6. WHEN an upload is rejected or fails, THE Frontend SHALL display a persistent inline error message describing the failure, which remains visible until the user initiates a new upload or explicitly dismisses it. IF a network request fails or times out, THE Frontend SHALL NOT retry automatically; THE Frontend SHALL display an error message and require the user to manually attempt the upload again.
7. WHEN a new file is successfully uploaded, THE Frontend SHALL clear any previously ingested document state — including extracted content and conversation history — and replace it with the new document.

---

### Requirement 2: File Type Detection and Routing

**User Story:** As a developer, I want the system to detect the file type of every upload and route it to the correct extractor, so that text is reliably extracted regardless of format.

#### Acceptance Criteria

1. WHEN a file is received by the Backend, THE Backend SHALL detect its type by inspecting magic bytes first; if magic bytes are inconclusive, THE Backend SHALL fall back to the declared MIME type. File extension alone SHALL NOT be used as the sole detection mechanism.
2. WHEN the detected type is PDF, THE Backend SHALL route extraction to the PDF Extractor.
3. WHEN the detected type is DOCX, THE Backend SHALL route extraction to the DOCX Extractor.
4. WHEN the detected type is PPTX, THE Backend SHALL route extraction to the PPTX Extractor.
5. WHEN the detected type resolves to plain text or Markdown (using the `.md` file extension as a tiebreaker when MIME type is `text/plain`), THE Backend SHALL route extraction to the Plain_Text Extractor.
6. IF the detected type does not match any supported format, THEN THE Backend SHALL return an HTTP 415 error with a message that names the detected type and lists the accepted types, without attempting extraction.
7. IF type detection itself fails due to a corrupt or unreadable file header, THEN THE Backend SHALL return an HTTP 422 error with a message indicating the file could not be read, without attempting extraction.

---

### Requirement 3: Text Extraction with Location Metadata

**User Story:** As a developer, I want each extractor to preserve location information, so that answers can cite the exact page or slide where information was found.

#### Acceptance Criteria

1. WHEN extracting a PDF, THE PDF_Extractor SHALL produce one text segment per page; each segment SHALL carry a `location` field set to the 1-based page number (a positive integer ≥ 1).
2. IF a PDF page is identified as a Scanned_Page (fewer than 50 extractable characters), THEN THE PDF_Extractor SHALL emit no segment for that page and SHALL log a warning that includes the page number.
3. WHEN extracting a DOCX, THE DOCX_Extractor SHALL produce one text segment per paragraph; each segment SHALL carry a `location` field set to `ceil(paragraph_index / 10)`, where `paragraph_index` is the 1-based ordinal of the paragraph in document order.
4. WHEN extracting a PPTX, THE PPTX_Extractor SHALL produce one text segment per slide; each segment SHALL carry a `location` field set to the 1-based slide number (a positive integer ≥ 1).
5. WHEN extracting a TXT or Markdown file, THE Plain_Text_Extractor SHALL produce a single text segment with no `location` field.
6. IF any extraction step raises an unhandled exception, THEN THE Backend SHALL return an HTTP 500 response whose body includes the source file name and the exception type, and SHALL NOT return a partial result silently.

---

### Requirement 4: Text Chunking

**User Story:** As a developer, I want extracted text to be chunked into semantically coherent units, so that each Chunk fits within embedding model limits and preserves meaning.

#### Acceptance Criteria

1. THE Chunker SHALL produce Chunks of no more than 500 words each.
2. THE Chunker SHALL apply an overlap of between 45 and 55 words between consecutive Chunks derived from the same source segment.
3. THE Chunker SHALL never split a Chunk at a mid-paragraph boundary; splits SHALL occur only at paragraph boundaries. IF a single paragraph exceeds 500 words, THEN THE Chunker SHALL split that paragraph at the nearest sentence boundary that keeps the Chunk within the 500-word limit.
4. WHEN a source segment is shorter than 500 words, THE Chunker SHALL treat the entire segment as a single Chunk without splitting.
5. THE Chunker SHALL attach the Document_ID, file type, and Location (if available) to every Chunk as metadata.
6. IF a source segment is empty or contains only whitespace, THEN THE Chunker SHALL log a warning that includes the Document_ID and the 1-based segment index, and SHALL continue processing remaining segments without emitting a Chunk for that segment.

---

### Requirement 5: Embedding Generation and Storage

**User Story:** As a developer, I want each Chunk to be embedded and stored in the Vector_Store, so that similarity search can retrieve relevant Chunks at query time.

#### Acceptance Criteria

1. WHEN the Chunker completes for a document, THE Embedder SHALL call the Gemini embedding model once per Chunk to generate a vector representation.
2. THE Embedder SHALL use the `GEMINI_API_KEY` environment variable for authentication and SHALL NOT hardcode credentials. IF `GEMINI_API_KEY` is absent or empty at invocation time, THE Backend SHALL return an HTTP 500 response with a message indicating the API key is not configured.
3. THE Vector_Store SHALL persist each Chunk's vector, text, Document_ID, file type, and Location as a single record. IF a Chunk has no Location (TXT/MD source), THE Vector_Store SHALL omit the Location field from the record rather than storing it as null or an empty string.
4. WHEN a new document is ingested with an existing Document_ID namespace, THE Vector_Store SHALL atomically replace all previously stored Chunks for that Document_ID with the new Chunks, such that no query can observe a mixed state of old and new Chunks.
5. IF the Gemini embedding API returns an error for any Chunk, THEN THE Backend SHALL abort the ingestion, roll back any Chunks already written for this Document_ID in the current operation, and return an HTTP 502 response whose body includes the index of the failed Chunk and the API error reason. IF the rollback operation itself fails, THE Backend SHALL still return HTTP 502 as specified.
6. WHEN ingestion completes successfully, THE Backend SHALL return an HTTP 200 response containing the Document_ID and the total number of Chunks stored.
7. IF the Vector_Store raises an error when writing any Chunk, THEN THE Backend SHALL abort the ingestion, roll back any Chunks already written for this Document_ID in the current operation, and return an HTTP 500 response with a message indicating a storage failure.
8. IF `GEMINI_API_KEY` is absent or empty when the Backend starts, THE Backend SHALL refuse to start, and SHALL log a startup warning indicating the key is missing.

---

### Requirement 6: Natural-Language Question Answering

**User Story:** As a user, I want to type a natural-language question about my uploaded document, so that I receive a concise, grounded answer.

#### Acceptance Criteria

1. WHILE a document has not been successfully ingested, THE Frontend SHALL disable the question text input and submit control, and SHALL display a label indicating that a document must be uploaded first.
2. WHEN the user submits a question, THE Frontend SHALL send it to the Backend via a `POST /ask` request containing the question text and the Document_ID.
3. WHEN the Backend receives a `POST /ask` request, THE Embedder SHALL generate an embedding for the question text.
4. WHEN the question embedding is ready, THE Retriever SHALL perform a similarity search in the Vector_Store scoped to the supplied Document_ID and return the top TOP_K_CHUNKS Chunks.
5. WHEN Chunks are retrieved, THE Generator SHALL construct a prompt that includes the retrieved Chunk texts and an instruction that directs the Gemini LLM to base its answer solely on the supplied chunks and to state when the answer is not present in them.
6. WHEN the LLM response is received, THE Backend SHALL return an HTTP 200 response containing the answer text, the list of Citations, and the list of retrieved Chunks.
7. IF no Chunks are retrieved for the supplied Document_ID, OR IF the answer is not found in the retrieved Chunks (as indicated by the LLM response containing the configured "not found" phrase), THEN THE Backend SHALL return an HTTP 200 response whose answer field contains the fixed phrase "The answer was not found in the uploaded document."
8. IF the Embedder or LLM API call fails during a query, THEN THE Backend SHALL return an HTTP 502 response with a message identifying which API call failed and the error reason.
9. IF the question text is empty or exceeds 2000 characters, THEN THE Backend SHALL return an HTTP 422 response with a message describing the invalid input, without calling any AI API.

---

### Requirement 7: Citations and Source Chunk Display

**User Story:** As a user, I want every answer to show which page or slide it came from and let me read the exact source text, so that I can verify the answer.

#### Acceptance Criteria

1. WHEN the Backend returns an answer, THE Backend SHALL include a deduplicated list of Citations; deduplication key is the Location value, so multiple Chunks from the same Location produce one Citation entry. Each Citation SHALL be formatted as "Page N" for PDF/DOCX sources and "Slide N" for PPTX sources, where N is the Location integer.
2. THE Frontend SHALL display the Citations list immediately below the answer text in the same message bubble or card, before any other UI elements.
3. WHEN the Backend returns retrieved Chunks, THE Frontend SHALL render each Chunk's full text, its Citation label (if available), and a 1-based rank label (e.g., "Source 1", "Source 2") inside the sources panel. IF any of these elements are missing for a Chunk, THE Frontend SHALL still display the Chunk with the available elements and omit only the missing ones.
4. IF a retrieved Chunk has no Location (TXT or Markdown source), THEN THE Frontend SHALL omit the Citation label for that Chunk rather than displaying a placeholder or null value.
5. THE Frontend SHALL render the sources panel in a collapsed state by default, allowing the user to expand it on demand.

---

### Requirement 8: Error Handling and User Feedback

**User Story:** As a user, I want clear inline error messages when something goes wrong, so that I know what happened and what to do next.

#### Acceptance Criteria

1. WHEN the Backend returns a 4xx or 5xx response, THE Frontend SHALL display a persistent inline error message adjacent to the UI zone that triggered the request (upload zone for upload errors, chat area for question errors); the message SHALL be a non-technical description that does not expose internal error codes or stack traces.
2. THE Frontend SHALL NOT use toast notifications or auto-dismissing alerts for error messages. This prohibition applies to all toast notification styles, including persistent toasts that require manual dismissal.
3. WHEN a new upload or question associated with an action is submitted successfully, THE Frontend SHALL clear the error message associated with that action.
4. IF a network request for upload or question submission does not receive a response within 30 seconds, THEN THE Frontend SHALL display a persistent inline message indicating the request could not be completed and suggesting the user retry.
5. WHEN an error state is active, THE Frontend SHALL keep the file input, upload submit control, and question submit control enabled so the user can retry without reloading the page.

---

### Requirement 9: Configuration and Security

**User Story:** As a developer, I want all secrets and tuneable parameters managed through environment variables, so that the application is secure and easy to configure across environments.

#### Acceptance Criteria

1. THE Backend SHALL read the Gemini API key exclusively from the `GEMINI_API_KEY` environment variable. IF `GEMINI_API_KEY` is absent or empty at startup, THE Backend SHALL log an error at startup and refuse to start. IF the key is present at startup but a subsequent runtime request fails due to the key being invalid or unauthorized, THE Backend SHALL return HTTP 500 for that request; runtime key failures SHALL be handled as request-level errors and SHALL NOT trigger a startup log.
2. THE Backend SHALL read the TOP_K_CHUNKS value from the `TOP_K_CHUNKS` environment variable; IF the variable is absent, non-numeric, or outside the range 1–20 inclusive, THE Backend SHALL use the default value of `5`.
3. THE Backend SHALL provide a `.env.example` file listing all required and optional environment variables with placeholder values.
4. THE Frontend SHALL read the backend base URL from the `NEXT_PUBLIC_API_URL` environment variable. IF `NEXT_PUBLIC_API_URL` is absent or empty at build time, THE Frontend SHALL log a build-time warning and fall back to `http://localhost:8000`.
5. THE Frontend SHALL provide a `.env.local.example` file listing the `NEXT_PUBLIC_API_URL` variable.
6. THE System SHALL include both `.env` and `.env.local` in `.gitignore` so that secrets are never committed to source control.

---

### Requirement 10: Round-Trip Integrity of Chunk Metadata

**User Story:** As a developer, I want to verify that chunk metadata (location, document ID, file type) survives the full ingestion pipeline without corruption, so that citations in answers are always accurate.

#### Acceptance Criteria

1. WHEN the Vector_Store retrieves any Chunk, THE retrieved Chunk's Document_ID, file type, and Location values SHALL be identical to those supplied during ingestion. For TXT/MD Chunks, the Location field SHALL be absent (not null, not an empty string). A Chunk ingested with file type TXT SHALL not be considered equivalent to a Chunk with file type MD; exact file type matching is required.
2. WHEN the Retriever returns Chunks for a given Document_ID, every returned Chunk SHALL carry a Document_ID equal to the queried Document_ID.
3. THE Chunker SHALL be idempotent: applying the Chunker to the same valid text input with the same configuration twice SHALL produce Chunks whose text content and metadata fields are identical in both runs.
