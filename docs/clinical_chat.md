# Phase 8.6: Multi-Turn Clinical Chat, Session Persistence & Cloud LLM Adapters

## 1. Overview

Phase 8.6 extends the grounded clinical RAG system into a persistent, multi-turn clinical consultation chat interface. It provides:
1. **Consultation Session & Message Persistence**: Backed authoritatively by PostgreSQL with Alembic migration `0008_create_chat_sessions_tables.py`.
2. **Multi-Turn Clinical Conversational Memory**: Passes prior turns in a consultation session into synthesis without losing grounded citations or patient isolation.
3. **Relevance & Confidence Filtering**: Supports `RAG_MIN_SIMILARITY` to drop low-confidence vector search results before synthesis.
4. **Cloud LLM Provider Adapters**: Concrete `OpenAILLMProvider` implementation supporting OpenAI and compatible chat completions endpoints.
5. **Zero-PHI Logging & Strict Isolation**: Preserves HIPAA-aligned clinical isolation and prompt injection defenses across all multi-turn dialogues.

---

## 2. Architecture & Data Flow

```
[Client / UI / Doctor / Patient]
               │
               ▼
[POST /api/v1/chat/sessions/{session_id}/messages]
               │
               ▼
   [RBAC & Patient Validation] ─── (Doctor clinical link, Patient self, Admin)
               │
               ▼
  [Record User Message Turn] ────► [PostgreSQL: chat_messages]
               │
               ▼
  [Load Recent Session Turns] ───► Multi-turn conversation context
               │
               ▼
 [Query Embedding + Vector Search] ──► [ChromaDB: patient-scoped]
               │
               ▼
 [Similarity Threshold Filter] ───► (Drop chunks with score < RAG_MIN_SIMILARITY)
               │
               ▼
 [SQL Chunk Ownership Check] ───► [PostgreSQL: document_chunks & medical_documents]
               │
               ▼
  [Grounded LLM Synthesis] ──────► BaseLLMProvider (MockLLM / OpenAILLMProvider)
               │
               ▼
  [Citation Verification] ───────► Strictly match source chunk IDs
               │
               ▼
[Record Assistant Message Turn] ──► [PostgreSQL: chat_messages]
               │
               ▼
  [Structured Chat Response]
```

---

## 3. Database Schema

### `chat_sessions` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | Primary Key, Autoincrement | Internal sequence ID |
| `session_id` | String(32) | Unique, Indexed | Public session identifier (`SES-YYYYMMDD-XXXX`) |
| `patient_id` | Integer | Foreign Key (`patients.id`), RESTRICT | Authoritative patient reference |
| `user_id` | Integer | Foreign Key (`users.id`), SET NULL | Creator user ID |
| `title` | String(255) | Default "Clinical Consultation" | Human-readable title |
| `is_active` | Boolean | Default `true` | Active/closed status |
| `created_at` | DateTime(timezone=True) | Default `now()` | Timestamp created |
| `updated_at` | DateTime(timezone=True) | Default `now()` | Timestamp last turn added |

### `chat_messages` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | Primary Key, Autoincrement | Internal sequence ID |
| `message_id` | String(32) | Unique, Indexed | Public message identifier (`MSG-YYYYMMDD-XXXX`) |
| `session_id` | Integer | Foreign Key (`chat_sessions.id`), CASCADE | Parent consultation session |
| `sender_role` | String(20) | Not Null | Author role (`user` or `assistant`) |
| `content` | Text | Not Null | Turn text content |
| `citations` | JSON | Nullable | Serialized list of verified `RAGCitation` objects |
| `insufficient_information` | Boolean | Default `false` | Fallback trigger flag |
| `retrieved_chunks` | Integer | Default `0` | Number of chunks evaluated |
| `created_at` | DateTime(timezone=True) | Default `now()` | Timestamp created |

---

## 4. API Reference

### 1. Create Consultation Session
- **Endpoint**: `POST /api/v1/chat/sessions`
- **Request Body**:
  ```json
  {
    "patient_id": "PAT-20260828-A1B2",
    "title": "Hypertension Medication Follow-up"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "session_id": "SES-20260828-98C7F012",
    "patient_id": "PAT-20260828-A1B2",
    "title": "Hypertension Medication Follow-up",
    "is_active": true,
    "message_count": 0,
    "created_at": "2026-08-28T14:15:00Z",
    "updated_at": "2026-08-28T14:15:00Z"
  }
  ```

### 2. List Patient Sessions
- **Endpoint**: `GET /api/v1/chat/sessions?patient_id=PAT-20260828-A1B2`
- **Response** (`200 OK`):
  ```json
  {
    "total": 1,
    "sessions": [
      {
        "session_id": "SES-20260828-98C7F012",
        "patient_id": "PAT-20260828-A1B2",
        "title": "Hypertension Medication Follow-up",
        "is_active": true,
        "message_count": 4,
        "created_at": "2026-08-28T14:15:00Z",
        "updated_at": "2026-08-28T14:20:00Z"
      }
    ]
  }
  ```

### 3. Get Session History
- **Endpoint**: `GET /api/v1/chat/sessions/{session_id}`
- **Response** (`200 OK`):
  Returns full session metadata and chronological array of `messages`.

### 4. Post Message Inquiry
- **Endpoint**: `POST /api/v1/chat/sessions/{session_id}/messages`
- **Request Body**:
  ```json
  {
    "message": "What is the dosage prescribed for Lisinopril?",
    "top_k": 5,
    "min_similarity": 0.0
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "message_id": "MSG-20260828-56E8A1D4",
    "session_id": "SES-20260828-98C7F012",
    "sender_role": "assistant",
    "content": "Based on the patient's medical records: Prescribed Medication: Lisinopril 20mg once daily in the morning.",
    "citations": [
      {
        "document_id": "DOCU-20260828-3B4F",
        "title": "Cardiology Summary",
        "page_number": 1,
        "chunk_id": "CHK-20260828-7A1B",
        "document_type": "consultation_note"
      }
    ],
    "insufficient_information": false,
    "retrieved_chunks": 1,
    "created_at": "2026-08-28T14:20:00Z"
  }
  ```

### 5. Close Consultation Session
- **Endpoint**: `DELETE /api/v1/chat/sessions/{session_id}`
- **Response** (`200 OK`):
  Sets `is_active: false` and returns updated session status.

---

## 5. Security & Isolation Matrix

| Actor | Session Access Policy |
|---|---|
| **Patient User** | Can only create, view, and query sessions for their own patient profile. Accessing another patient's session returns `403 Forbidden`. |
| **Doctor User** | Can create, view, and query sessions only for patients with whom they have an active clinical relationship (verified doctor profile linked via appointment or encounter). Unlinked doctor queries return `403 Forbidden`. |
| **Healthcare Staff / Admin** | Unrestricted access across all patient sessions for auditing and operational care management. |
| **Direct Vector Isolation** | Vector similarity queries are filtered by `patient_id` metadata and verified against PostgreSQL ownership. |
