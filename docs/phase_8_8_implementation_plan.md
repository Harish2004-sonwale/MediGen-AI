# Phase 8.8 Implementation Plan: Streaming Clinical Responses, OCR Integration & AWS Bedrock

## 1. Current Architecture Overview

MediGen-AI is a clinically grounded AI medical assistant with a multi-layered security architecture:
- **Core Framework**: FastAPI async REST framework with dependency injection and JWT RBAC (`patient`, `doctor`, `healthcare_staff`, `admin`).
- **Authoritative Data Layer**: PostgreSQL holding users, doctors, appointments, encounters, patients, medical documents, chunks, chat sessions, and messages.
- **Retrieval & Semantic Layer**: ChromaDB with mandatory `patient_id` metadata isolation, verified against PostgreSQL ownership before LLM synthesis.
- **Synthesis Layer**: `BaseLLMProvider` with `MockLLMProvider` and `OpenAILLMProvider`, implementing strict clinical grounding, prompt injection defenses, structured citation extraction, and multi-turn conversational history.
- **Document Ingestion**: Multi-format text extraction (PDF, DOCX, TXT), semantic chunking, and embedding indexing.

---

## 2. Existing Reusable Components

- `app.services.rag_service.validate_patient_rag_access`: RBAC & doctor active clinical relationship validation.
- `app.services.rag_service.execute_rag_query`: RAG pipeline (embedding query, similarity search with `RAG_MIN_SIMILARITY`, SQL chunk ownership verification, context building, LLM synthesis, citation extraction).
- `app.services.chat_service`: Session resolution, message persistence, multi-turn history loading, and session closing.
- `app.ai.extractors`: Existing `extract_pdf_text`, `extract_docx_text`, `extract_txt_text`.
- `app.ai.cleaner` & `app.ai.chunker`: Text normalization and token-aware semantic chunking.
- `app.ai.embeddings` & `app.ai.vector_store`: Embeddings generation and ChromaDB persistence.
- `app.ai.llm`: Base classes, `GroundedContextChunk`, `CitationData`, `LLMGroundedResponse`.

---

## 3. Files Requiring Modification

1. **`backend/requirements.txt`**: Add `boto3>=1.34.0,<2.0.0`.
2. **`backend/app/core/config.py`**:
   - Add OCR settings: `OCR_ENABLED: bool = False`, `OCR_PROVIDER: str = "mock"`.
   - Add AWS & Bedrock settings: `AWS_REGION: str = "us-east-1"`, `AWS_ACCESS_KEY_ID: Optional[str] = None`, `AWS_SECRET_ACCESS_KEY: Optional[str] = None`, `BEDROCK_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"`.
3. **`backend/.env.example`**: Document new OCR and Bedrock configuration keys.
4. **`backend/app/ai/extractors.py`**:
   - Detect image-only/scanned PDFs (e.g. 0 extractable characters from standard text stream).
   - If `OCR_ENABLED` is true, invoke configured OCR provider; otherwise cleanly handle fallback.
5. **`backend/app/ai/llm.py`**:
   - Add `generate_grounded_response_stream(...) -> Iterator[str | LLMStreamDelta]` to `BaseLLMProvider`.
   - Update `MockLLMProvider` with streaming support.
   - Update `OpenAILLMProvider` with streaming support.
   - Implement `BedrockLLMProvider` with boto3 runtime client supporting invocation & response streaming.
   - Update `get_llm_provider` factory to support `"bedrock"`.
6. **`backend/app/services/chat_service.py`**:
   - Implement `stream_chat_message(...)` generator returning structured SSE events (`start`, `delta`, `citation`, `done`, `error`) and transactionally persisting the user and final assistant message.
7. **`backend/app/api/v1/endpoints/chat.py`**:
   - Add `POST /api/v1/chat/sessions/{session_id}/messages/stream` returning `StreamingResponse(..., media_type="text/event-stream")`.
8. **`backend/app/ai/__init__.py`** & **`backend/app/schemas/__init__.py`**: Export new classes and types.

---

## 4. New Files Required

1. **`backend/app/ai/ocr.py`**:
   - `BaseOCRProvider` (abstract base for OCR).
   - `MockOCRProvider` (deterministic, test-friendly OCR extraction from image/scanned bytes).
   - `TextractOCRProvider` (optional AWS Textract adapter boundary).
   - `get_ocr_provider(...)` factory.
2. **`backend/tests/test_streaming_chat.py`**:
   - Tests for SSE streaming endpoints, RBAC, isolation, citation streaming, multi-turn memory, client disconnect/failure handling.
3. **`backend/tests/test_ocr.py`**:
   - Tests for scanned PDF detection, OCR provider extraction, chunking, and ChromaDB indexing.
4. **`backend/tests/test_bedrock.py`**:
   - Tests for `BedrockLLMProvider` initialization, boto3 mocking, generation, citations, prompt injection defense, and streaming.
5. **`docs/phase_8_8.md`**: Phase 8.8 milestone documentation and validation report.

---

## 5. Database Changes

**Evaluation**:
The existing `chat_messages` table (created in Migration 0008) already contains:
- `id`, `message_id`, `session_id`, `sender_role`, `content`, `citations` (JSON), `insufficient_information`, `retrieved_chunks`, `created_at`.
During streaming, the user message is persisted upon request receipt, tokens are streamed via SSE, and the final complete assistant message with validated citations is persisted upon completion.
**Conclusion**: No database schema change or new Alembic migration is necessary.

---

## 6. API Changes

- **New Endpoint**: `POST /api/v1/chat/sessions/{session_id}/messages/stream`
  - **Headers**: `Authorization: Bearer <JWT>`, `Accept: text/event-stream`
  - **Body**: `ChatMessageCreate` (`message`, `top_k`, `min_similarity`)
  - **Response**: `text/event-stream` (Server-Sent Events)
    - `event: start\ndata: {"session_id":"...", "message_id":"..."}\n\n`
    - `event: delta\ndata: {"text":"..."}\n\n`
    - `event: citation\ndata: {"document_id":"...", "title":"...", "chunk_id":"..."}\n\n`
    - `event: done\ndata: {"message_id":"...", "completed":true, "insufficient_information":false, "retrieved_chunks":N}\n\n`
    - `event: error\ndata: {"error":"..."}\n\n`
- **Existing Endpoints**: `POST /api/v1/chat/sessions/{session_id}/messages` and all RAG/document endpoints remain 100% unchanged.

---

## 7. Security & PHI Protection

- **Patient & Doctor RBAC**: Enforced identically in both non-streaming and streaming handlers before processing or retrieval.
- **Zero-PHI Logging**: Operational logs output only message IDs, turn counts, and elapsed durations. No raw document chunks, prompts, SSE deltas, or embeddings are logged.
- **Prompt Injection Defense**: Maintained in `BedrockLLMProvider` and streaming synthesizers via inert XML `<document_context>` wrappers and instruction refusal rules.
- **Path Traversal & Safe Exceptions**: Exception handlers never expose local filesystem paths, database connection strings, or cloud access keys in SSE events or HTTP responses.

---

## 8. Testing Strategy

1. **SSE Streaming Tests**:
   - Verify event sequence: `start` -> `delta`s -> `citation`s -> `done`.
   - Verify patient isolation (Patient A denied access to Patient B's session stream).
   - Verify unauthorized doctor denied access to unlinked patient stream.
   - Verify transactional persistence: both user message and assistant message saved in SQLite/PostgreSQL with verified citations.
   - Verify error event emission when session is closed or query fails.
2. **OCR Tests**:
   - Normal text PDFs process without invoking OCR.
   - Scanned image-only PDFs trigger OCR when `OCR_ENABLED=True`.
   - `MockOCRProvider` returns structured `ExtractedDocument` preserving page numbers.
   - OCR text flows through standard cleaning -> chunking -> vector indexing seamlessly.
   - Failure when OCR disabled or unextractable scanned PDF.
3. **Bedrock LLM Provider Tests**:
   - Factory instantiates `BedrockLLMProvider` when `LLM_PROVIDER="bedrock"`.
   - Mock boto3 client responses for Claude / Titan invocation.
   - Verify grounded synthesis, citation extraction, multi-turn history handling, and streaming.
   - Verify execution without AWS credentials in unit/CI tests.
4. **Regression & Full Suite**:
   - All 136 existing tests + new Phase 8.8 tests must pass.

---

## 9. Backward Compatibility

- Existing endpoints (`/api/v1/documents/*`, `/api/v1/rag/*`, `/api/v1/chat/sessions`, `/api/v1/chat/sessions/{id}/messages`) remain intact with identical signatures and behavior.
- Default settings keep `OCR_ENABLED=False` and `LLM_PROVIDER="mock"` for zero-dependency local testing and CI.

---

## 10. Implementation Order

1. **Dependencies & Configuration**: Update `requirements.txt`, `config.py`, and `.env.example`.
2. **OCR Subsystem**: Implement `app/ai/ocr.py` and update `app/ai/extractors.py`.
3. **Bedrock LLM Adapter & Streaming Abstraction**: Enhance `app/ai/llm.py` with streaming generator and `BedrockLLMProvider`.
4. **Streaming Chat Service & API Endpoint**: Implement SSE streaming in `app/services/chat_service.py` and `app/api/v1/endpoints/chat.py`.
5. **Testing Suite**: Create `test_streaming_chat.py`, `test_ocr.py`, and `test_bedrock.py`.
6. **Validation**: Run full pytest suite, verify Alembic migration integrity, clean `git diff --check`.
7. **Documentation**: Deliver `docs/phase_8_8.md` and update `docs/api_overview.md` and `docs/deployment.md`.
