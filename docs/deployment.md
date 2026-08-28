# MediGen-AI: Production Deployment & Operations Guide

## 1. System Architecture

MediGen-AI is designed with a decoupled, HIPAA-conscious architecture:
- **FastAPI Core**: Asynchronous REST API service handling authentication, RBAC, medical records CRUD, and RAG/chat orchestration.
- **Authoritative Data Store (PostgreSQL)**: Stores all clinical entities, users, patients, doctors, appointments, encounters, document metadata, document chunks, chat sessions, and messages.
- **Semantic Retrieval Layer (ChromaDB)**: Local persistent vector store holding patient-scoped embedding vectors.
- **LLM Synthesis Providers**: Configurable via `BaseLLMProvider` (`mock` for deterministic testing/air-gapped deployments, `openai`/cloud adapter for cloud inference).

---

## 2. Environment Configuration

Create a production `.env` file based on `.env.example`:

```ini
# Application Configuration
PROJECT_NAME="MediGen AI"
VERSION="0.1.0"
ENVIRONMENT="production"
DEBUG=False

# Server Configuration
HOST="0.0.0.0"
PORT=8000
API_V1_STR="/api/v1"

# PostgreSQL Database Configuration
DATABASE_URL="postgresql+psycopg://postgres_user:STRONG_PRODUCTION_PASSWORD@db-host:5432/medigen_ai"
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_CONNECT_TIMEOUT=5

# JWT & Authentication Configuration
JWT_SECRET_KEY="A_VERY_SECURE_RANDOM_SECRET_KEY_MIN_32_CHARS"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Medical Document Storage & Chunking
DOCUMENT_STORAGE_PATH="/var/data/medigen/medical_documents"
MAX_DOCUMENT_SIZE_MB=10
DOCUMENT_CHUNK_SIZE_TOKENS=500
DOCUMENT_CHUNK_OVERLAP_TOKENS=100

# Vector Database & Embedding Configuration
EMBEDDING_PROVIDER="mock"
EMBEDDING_DIMENSION=384
VECTOR_DB_PATH="/var/data/medigen/vector_db"
VECTOR_COLLECTION_NAME="medical_documents"

# Clinical RAG & LLM Configuration
LLM_PROVIDER="mock"
LLM_MODEL="medigen-clinical-v1"
RAG_TOP_K=5
RAG_MIN_SIMILARITY=0.0
RAG_MAX_CONTEXT_CHUNKS=10
CHAT_HISTORY_MAX_TURNS=5
OPENAI_API_KEY=""
OPENAI_BASE_URL=""
```

---

## 3. Database Migrations

Apply Alembic migrations sequentially before launching application workers:

```bash
cd backend
alembic upgrade head
```

To inspect raw SQL statements prior to execution:
```bash
alembic upgrade head --sql
```

---

## 4. Running the Application

### Using Uvicorn in Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Persistent Volume Requirements
Ensure the following directories exist with appropriate read/write permissions for the application user:
- `DOCUMENT_STORAGE_PATH` (e.g. `/var/data/medigen/medical_documents`)
- `VECTOR_DB_PATH` (e.g. `/var/data/medigen/vector_db`)

---

## 5. Security & Operational Checklist

- [ ] `DEBUG=False` set in production environment.
- [ ] `JWT_SECRET_KEY` set to a cryptographically strong secret.
- [ ] Database credentials not committed to version control.
- [ ] Storage and vector directories hosted on encrypted volumes.
- [ ] SSL/TLS terminated at ingress / reverse proxy (Nginx / ALB).
- [ ] Operational logging configured (log level `INFO`); verify logs contain zero PHI.
