# Vector Database Integration — MediGen AI Phase 8.4

## Overview

Phase 8.4 integrates a vector database and embedding pipeline into MediGen AI's clinical document processing system. After text extraction and semantic chunking (Phase 8.3), each `DocumentChunk` is embedded into a dense vector representation and indexed in ChromaDB for future semantic retrieval.

The database (PostgreSQL) remains the **authoritative source of truth** for all document metadata and chunk content. ChromaDB is the **retrieval/index layer only**.

---

## Architecture

```
MedicalDocument (uploaded file)
      │
      ▼
Text Extraction (PDF / DOCX / TXT)  ← Phase 8.3
      │
      ▼
Clinical Text Cleaning              ← Phase 8.3
      │
      ▼
Semantic Chunking → DocumentChunk[] ← Phase 8.3
      │
      ▼
Embedding Provider                  ← Phase 8.4
 (MockEmbeddingProvider / future real provider)
      │
      ▼
ChromaVectorStore (ChromaDB)        ← Phase 8.4
 ┌────────────────────────┐
 │ metadata per vector:   │
 │  patient_id            │
 │  document_id           │
 │  chunk_id              │
 │  chunk_index           │
 │  page_number           │
 │  document_type         │
 └────────────────────────┘
      │
      ▼
vector_id saved to DocumentChunk.vector_id ← Phase 8.4
      │
      ▼
Document status → COMPLETED
      │
      ▼
Patient-filtered Semantic Search    ← Phase 8.5
```

---

## Embedding Abstraction

### `BaseEmbeddingProvider` (abstract)

Located at `backend/app/ai/embeddings.py`.

| Method | Description |
|---|---|
| `embed_documents(texts)` | Batch embed a list of strings → `list[list[float]]` |
| `embed_query(text)` | Embed a single query string → `list[float]` |
| `dimension` (property) | Return fixed embedding dimension |

### `MockEmbeddingProvider`

- **No cloud dependency** — works offline, no API keys required.
- **Deterministic** — uses `hashlib.SHA-256` (not Python's `hash()`) so vectors are identical across processes and platforms.
- **Unit normalised** — L2 normalised to unit length, suitable for cosine similarity.
- **Configurable dimension** — defaults to 384.

```python
from app.ai.embeddings import MockEmbeddingProvider

provider = MockEmbeddingProvider(dimension=384)
vec = provider.embed_query("Patient has type 2 diabetes.")
# vec is always the same for this text, regardless of process/platform
```

### Factory

```python
from app.ai.embeddings import get_embedding_provider

provider = get_embedding_provider(
    provider=settings.EMBEDDING_PROVIDER,   # "mock"
    dimension=settings.EMBEDDING_DIMENSION, # 384
)
```

### Adding a Real Provider

Subclass `BaseEmbeddingProvider` and register it in `get_embedding_provider()`:

```python
class BedrockEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model_id: str, region: str, dimension: int) -> None: ...
    def embed_documents(self, texts): ...
    def embed_query(self, text): ...
    @property
    def dimension(self): ...
```

No other code needs to change.

---

## ChromaDB Vector Store

### `BaseVectorStore` (abstract)

Located at `backend/app/ai/vector_store.py`.

| Method | Description |
|---|---|
| `upsert(vector_ids, embeddings, metadatas, documents)` | Add/update vectors |
| `similarity_search(query_embedding, patient_id, top_k, ...)` | Patient-scoped search |
| `delete_by_document(document_id)` | Remove all vectors for a document |
| `delete_by_vector_ids(vector_ids)` | Remove specific vectors |
| `count(patient_id=None)` | Count vectors |
| `health_check()` | Returns `{"healthy": bool, ...}` — no filesystem paths |

### `ChromaVectorStore`

- **Persistent local storage** under `VECTOR_DB_PATH` (default `data/vector_db`).
- **Cosine similarity** space (`hnsw:space=cosine`).
- Uses `get_or_create_collection` so restarts are idempotent.
- Internal file paths are **never included in API responses or health check output**.

### Factory

```python
from app.ai.vector_store import get_vector_store

store = get_vector_store(
    db_path=settings.VECTOR_DB_PATH,
    collection_name=settings.VECTOR_COLLECTION_NAME,
)
```

---

## Metadata Structure

Every vector stored in ChromaDB carries the following metadata:

| Field | Type | Description |
|---|---|---|
| `patient_id` | `str` | Patient database ID — **required for isolation** |
| `document_id` | `str` | Public document ID (e.g. `DOCU-20260828-A1B2`) |
| `chunk_id` | `str` | Public chunk ID (e.g. `CHK-20260828-C3D4`) |
| `chunk_index` | `int` | Sequential index within the document |
| `page_number` | `int` | Source page number (`-1` if unknown) |
| `document_type` | `str` | Clinical classification (e.g. `lab_report`) |

---

## Patient Isolation

**Patient-level isolation is mandatory and enforced at the vector store layer.**

1. Every `upsert()` call **requires** `patient_id` in each metadata dict (raises `ValueError` otherwise).
2. Every `similarity_search()` call **requires** a non-empty `patient_id` (raises `ValueError` otherwise).
3. ChromaDB's `where` filter always includes `{"patient_id": {"$eq": patient_id}}`.
4. It is **architecturally impossible** to perform a global search that spans multiple patients.

```python
# Cross-patient search is forbidden — this raises ValueError
store.similarity_search(query_embedding=vec, patient_id="")
```

---

## Indexing Lifecycle

```
1. Document upload / reprocess triggered
2. process_medical_document() called
3. Status → PROCESSING
4. Text extracted from file
5. Text chunked into DocumentChunk records
6. Old vectors removed from ChromaDB (idempotency)
7. Old chunks deleted from database (idempotency)
8. New chunks saved to database (vector_id = NULL)
9. index_document_chunks() called
   a. Batch embed all chunk texts
   b. Upsert vectors with patient metadata
   c. Write vector_id back to DocumentChunk records
10. Document status → COMPLETED
```

---

## Reprocessing Lifecycle

`POST /api/v1/documents/{document_id}/reprocess`

Calls `process_medical_document()` which is idempotent:

1. Remove existing vectors from ChromaDB for the document.
2. Delete existing `DocumentChunk` records for the document.
3. Re-extract text from the stored file.
4. Re-chunk the text.
5. Save new chunks.
6. Embed and upsert new vectors.
7. Save new vector IDs.
8. Update `total_chunks`.
9. Mark document `COMPLETED`.

**Repeated reprocessing never creates duplicate vectors** — ChromaDB `upsert` by chunk_id overwrites existing vectors.

---

## Deletion Lifecycle

`DELETE /api/v1/documents/{document_id}`

`delete_medical_document()` performs:

1. **RBAC check** (existing authorization).
2. **Vector cleanup** — `remove_document_vectors()` calls `vector_store.delete_by_document()`.
3. **Physical file deletion** — removes the stored file from disk.
4. **Database deletion** — `db.delete(document)` with cascade to `DocumentChunk`.

If vector deletion fails, a warning is logged and the function does **not** silently claim complete cleanup. The document and file are still deleted.

---

## Configuration

All values are environment-variable configurable. Add to `.env`:

```ini
EMBEDDING_PROVIDER=mock
EMBEDDING_DIMENSION=384
VECTOR_DB_PATH=data/vector_db
VECTOR_COLLECTION_NAME=medical_documents
VECTOR_TOP_K=5
```

| Setting | Default | Description |
|---|---|---|
| `EMBEDDING_PROVIDER` | `mock` | Provider name (`mock` for now) |
| `EMBEDDING_DIMENSION` | `384` | Vector dimension |
| `VECTOR_DB_PATH` | `data/vector_db` | ChromaDB storage directory |
| `VECTOR_COLLECTION_NAME` | `medical_documents` | ChromaDB collection name |
| `VECTOR_TOP_K` | `5` | Default similarity search results |

---

## Security Considerations

1. **No medical content in logs** — chunk text and embeddings are never written to application logs.
2. **Patient isolation is mandatory** — all searches are patient-scoped; global searches are rejected.
3. **No API path exposure** — ChromaDB storage paths are never returned in health check or API responses.
4. **RBAC preserved** — all existing document and chunk authorization checks are unchanged.
5. **Metadata-only ChromaDB** — chunk content is stored in PostgreSQL (authoritative). ChromaDB stores only text for reference; retrieval results reference chunk_id for DB lookup.

---

## Future Migration Path

The `BaseEmbeddingProvider` and `BaseVectorStore` abstractions allow future migration without changing the RAG service or API layer:

| Backend | Migration Step |
|---|---|
| **pgvector** | Implement `PgVectorStore(BaseVectorStore)` using SQLAlchemy + `pgvector` extension |
| **AWS OpenSearch** | Implement `OpenSearchVectorStore(BaseVectorStore)` using `opensearch-py` |
| **AWS Bedrock Embeddings** | Implement `BedrockEmbeddingProvider(BaseEmbeddingProvider)` using `boto3` |
| **OpenAI Embeddings** | Implement `OpenAIEmbeddingProvider(BaseEmbeddingProvider)` using `openai` |

Register the new class in `get_embedding_provider()` or `get_vector_store()` and update `EMBEDDING_PROVIDER` / `VECTOR_BACKEND` in `.env`. No service layer changes required.

---

## Health Check

```python
store = get_vector_store(settings.VECTOR_DB_PATH, settings.VECTOR_COLLECTION_NAME)
health = store.health_check()
# Returns: {"healthy": True, "collection_name": "...", "vector_count": N, "provider": "chromadb"}
```

The health check can be integrated into a protected admin endpoint. It **does not** expose filesystem paths.

---

## Files Added / Modified (Phase 8.4)

| File | Role |
|---|---|
| `backend/app/ai/embeddings.py` | Embedding abstraction + MockEmbeddingProvider |
| `backend/app/ai/vector_store.py` | Vector store abstraction + ChromaVectorStore |
| `backend/app/ai/__init__.py` | Updated exports |
| `backend/app/services/vector_indexing_service.py` | Chunk → embed → upsert pipeline |
| `backend/app/services/document_processing_service.py` | Wired vector indexing after chunking |
| `backend/app/services/document_service.py` | Added vector cleanup on deletion |
| `backend/app/services/__init__.py` | Updated exports |
| `backend/app/core/config.py` | Added vector + embedding settings |
| `backend/requirements.txt` | Added `chromadb>=0.5.0,<1.0.0` |
| `backend/tests/test_embeddings.py` | Embedding provider tests |
| `backend/tests/test_vector_store.py` | Vector store tests (incl. patient isolation) |
| `backend/tests/test_vector_indexing.py` | Indexing pipeline integration tests |
| `docs/vector_database.md` | This document |
