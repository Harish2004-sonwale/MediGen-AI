# MediGen AI - Clinical Decision Support System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/Auth-JWT%20%2B%20Bcrypt-orange.svg)](docs/authentication.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MediGen AI is an AI-powered Clinical Decision Support System (CDSS) designed to assist healthcare professionals with:
- Patient information management
- Doctor profile verification and department discovery
- Clinical appointment scheduling and conflict prevention
- Medical document analysis
- Clinical knowledge retrieval
- AI-assisted documentation
- Decision-support insights

---

## ⚕️ Healthcare Safety & Assistive Disclaimer

> [!IMPORTANT]
> **MediGen AI is designed strictly as an assistive clinical decision support tool.**
> All AI-generated outputs, analyses, summaries, and suggestions must undergo rigorous review and verification by certified healthcare professionals before any clinical application or treatment decision. MediGen AI does not provide standalone diagnostic determinations or replace professional medical judgment. Clinician-authored medical records remain strictly distinguishable and segregated from AI-generated assistance.

---

## 📌 Current Development Status

- **Milestone 1 — Initial Backend Foundation**: Completed & Pushed ✅
- **Milestone 2 — PostgreSQL Database Foundation**: Completed & Pushed ✅
- **Milestone 3 — Authentication & User Roles**: Completed & Pushed ✅
- **Milestone 4 — Patient Management**: Completed & Pushed ✅
- **Milestone 5 — Medical Records & Clinical Encounters**: Completed & Pushed ✅
- **Milestone 6 — Doctor Management & Department Discovery**: Completed & Verified ✅
- **Milestone 7 — Appointment Scheduling & Care Team Allocation**: Completed & Verified ✅
  - [x] Appointment ORM model with foreign keys to Patient & Doctor (`ondelete="RESTRICT"`)
  - [x] Appointment status lifecycle (`scheduled`, `confirmed`, `completed`, `cancelled`, `rejected`)
  - [x] Conflict prevention (validates future time & prevents overlapping doctor bookings)
  - [x] Role-based permissions (patients view own, doctors view assigned, admin/staff manage all)
  - [x] Alembic migration (`0006_create_appointments_table.py`)
  - [x] Comprehensive automated test suite (46 unit tests, 2 live integration tests)
  - [x] Module documentation ([`docs/appointments.md`](docs/appointments.md))
- **Milestone 8 — Clinical AI, RAG & Clinical Intelligence**: Completed & Verified ✅
  - **Phase 8.5 — Clinical RAG**: Patient-scoped RAG, query embeddings, ChromaDB vector retrieval, PostgreSQL authoritative verification, grounded LLM synthesis, citation validation, prompt injection defense, cross-patient isolation, RBAC, and zero-PHI operational logging.
  - **Phase 8.6 — Multi-Turn Clinical Chat**: Persistent chat sessions & messages, multi-turn conversational memory, RAG + conversation history grounding, patient RBAC, citation persistence, and cloud LLM adapter architecture.
  - **Phase 8.7 — Production Hardening & E2E Validation**: End-to-end document ingestion & RAG pipeline, persistent ChromaDB vector lifecycle management, cross-patient isolation, path traversal protection, deployment and API documentation.
  - **Phase 8.8 — Streaming, OCR & AWS Bedrock**: Server-Sent Events (SSE) clinical response streaming, pluggable OCR architecture with Mock and optional AWS Textract adapter boundaries, and AWS Bedrock LLM provider (Claude/Titan models with streaming support). *(AWS integrations are optional cloud adapters).*
  - **Phase 8.9 — Longitudinal Clinical Intelligence & Safety**: Comprehensive patient clinical timeline, historical clinical event aggregation, RAG-grounded longitudinal summaries, medication duplication detection, allergy warning conflict detection, extensible drug-drug interaction & contraindication provider architecture, and strict clinician-review safety boundaries.

---

## 🛠️ Technology Stack

- **Language:** Python 3.11+
- **API Framework:** FastAPI (>=0.110.0)
- **ASGI Server:** Uvicorn (>=0.28.0)
- **ORM & Database:** SQLAlchemy 2.0 (>=2.0.28), Psycopg 3 (>=3.1.18), PostgreSQL (14+)
- **Vector Database:** ChromaDB (>=0.4.24)
- **Migrations:** Alembic (>=1.13.0)
- **Security & Auth:** PyJWT (>=2.8.0), Bcrypt (>=4.0.1), Email-Validator (>=2.1.0)
- **Settings & Validation:** Pydantic (>=2.6.0), Pydantic Settings (>=2.2.0)
- **Testing & Client:** Pytest (>=8.0.0), HTTPX (>=0.27.0)

---

## 📁 Repository Structure

```text
MediGen-AI/
├── backend/
│   ├── alembic/           # Alembic database migrations
│   │   ├── versions/      # Migration scripts
│   │   │   ├── 0001_create_users_table.py
│   │   │   ├── 0002_create_patients_table.py
│   │   │   ├── 0003_create_encounters_table.py
│   │   │   ├── 0004_create_doctors_table.py
│   │   │   ├── 0005_add_doctor_department.py
│   │   │   ├── 0006_create_appointments_table.py
│   │   │   ├── 0007_create_medical_documents_table.py
│   │   │   └── 0008_create_chat_sessions_tables.py
│   │   └── env.py         # Migration environment configuration
│   ├── app/
│   │   ├── ai/            # AI pipelines, RAG, embeddings, OCR, LLM adapters
│   │   ├── api/           # API routers & endpoints
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── appointments.py # Appointment scheduling endpoints
│   │   │   │   │   ├── auth.py         # Authentication endpoints
│   │   │   │   │   ├── chat.py         # Multi-turn clinical chat & streaming
│   │   │   │   │   ├── doctors.py      # Doctor management endpoints
│   │   │   │   │   ├── documents.py    # Document upload & processing endpoints
│   │   │   │   │   ├── encounters.py   # Clinical encounter endpoints
│   │   │   │   │   ├── patients.py     # Patient management endpoints
│   │   │   │   │   ├── rag.py          # Clinical RAG query endpoints
│   │   │   │   │   ├── safety.py       # Clinical safety & drug check endpoints
│   │   │   │   │   └── timeline.py     # Longitudinal timeline endpoints
│   │   │   │   └── api.py              # API v1 router aggregator
│   │   │   └── deps.py    # Auth & role-checking dependencies
│   │   ├── core/          # Configuration & security
│   │   ├── database/      # Database foundation
│   │   ├── models/        # Database ORM models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic services
│   │   └── main.py        # FastAPI entrypoint
│   ├── tests/             # Automated test suite (163 tests, 100% passing)
│   ├── .env.example       # Environment configuration template
│   ├── alembic.ini        # Alembic configuration
│   ├── pytest.ini         # Pytest configuration
│   └── requirements.txt   # Backend dependencies
├── docs/                  # Architecture & system documentation
│   ├── appointments.md    # Appointment scheduling documentation
│   ├── authentication.md  # Auth & RBAC documentation
│   ├── database.md        # PostgreSQL database guide
│   ├── doctors.md         # Doctor management documentation
│   ├── medical_records.md # Clinical encounters documentation
│   ├── patients.md        # Patient management documentation
│   ├── documents.md       # Document upload and management
│   ├── document_processing.md # Chunking and text extraction
│   ├── vector_database.md # Vector database and indexing
│   ├── rag.md             # Clinical RAG architecture
│   ├── clinical_chat.md   # Multi-turn chat and streaming
│   ├── clinical_timeline.md # Longitudinal timeline aggregation
│   ├── clinical_safety.md # Clinical safety and interaction checks
│   ├── deployment.md      # Deployment guide
│   └── api_overview.md    # Full API reference
├── LICENSE                # MIT License
└── README.md              # Project documentation
```

---

## 📡 API Endpoints

| Method | Endpoint | Access | Description | Status Code |
|---|---|---|---|---|
| `GET` | `/` | Public | API Root / Welcome | `200 OK` |
| `GET` | `/health` | Public | Application Health Check | `200 OK` |
| `GET` | `/health/db` | Public | PostgreSQL Database Connectivity Check | `200 OK` / `503 Unavailable` |
| `POST` | `/api/v1/auth/register` | Public | Register new user | `201 Created` |
| `POST` | `/api/v1/auth/login` | Public | Login and obtain JWT Bearer Token | `200 OK` |
| `GET` | `/api/v1/auth/me` | Authenticated | Get current user profile | `200 OK` |
| `GET` | `/api/v1/auth/health` | Public | Auth Module Health Check | `200 OK` |
| `POST` | `/api/v1/doctors` | Admin / Doctor | Register doctor profile | `201 Created` |
| `GET` | `/api/v1/doctors` | Authenticated | Search and discover doctors across departments | `200 OK` |
| `GET` | `/api/v1/doctors/me` | Doctor / Admin | Retrieve own doctor profile | `200 OK` |
| `PATCH` | `/api/v1/doctors/me` | Doctor / Admin | Update own professional profile | `200 OK` |
| `GET` | `/api/v1/doctors/{doctor_id}` | Authenticated | Retrieve doctor profile | `200 OK` |
| `PATCH` | `/api/v1/doctors/{doctor_id}` | Admin / Doctor | Update doctor profile | `200 OK` |
| `DELETE` | `/api/v1/doctors/{doctor_id}` | Admin | Soft-deactivate doctor profile | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/verify` | Admin | Verify doctor credentials | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/reject` | Admin | Reject doctor verification application | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/activate` | Admin / Doctor | Set doctor availability to available | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/deactivate`| Admin / Doctor | Set doctor availability to unavailable | `200 OK` |
| `POST` | `/api/v1/patients` | Clinical Roles | Register new patient record | `201 Created` |
| `GET` | `/api/v1/patients` | Clinical Roles | Search and list patients (paginated) | `200 OK` |
| `GET` | `/api/v1/patients/{patient_id}` | Clinical Roles | Retrieve patient profile by patient_id | `200 OK` |
| `PATCH` | `/api/v1/patients/{patient_id}` | Clinical Roles | Update patient demographic details | `200 OK` |
| `DELETE` | `/api/v1/patients/{patient_id}` | Admin / Doctor | Soft-delete / deactivate patient record | `200 OK` |
| `POST` | `/api/v1/patients/{patient_id}/encounters` | Clinical Roles | Record a new clinical encounter for patient | `201 Created` |
| `GET` | `/api/v1/patients/{patient_id}/encounters` | Clinical Roles | List chronological encounters for patient | `200 OK` |
| `GET` | `/api/v1/encounters/{encounter_id}` | Clinical Roles | Retrieve encounter details by encounter identifier | `200 OK` |
| `PATCH` | `/api/v1/encounters/{encounter_id}` | Clinical Roles | Update encounter notes, assessment, plan | `200 OK` |
| `POST` | `/api/v1/appointments` | Authenticated | Schedule a new appointment | `201 Created` |
| `GET` | `/api/v1/appointments` | Authenticated | List and filter appointments | `200 OK` |
| `GET` | `/api/v1/appointments/{appointment_id}` | Authenticated | Get appointment details | `200 OK` |
| `PATCH` | `/api/v1/appointments/{appointment_id}` | Admin / Staff / Doctor | Reschedule / update appointment | `200 OK` |
| `POST` | `/api/v1/appointments/{appointment_id}/confirm` | Admin / Staff / Doctor | Confirm scheduled appointment | `200 OK` |
| `POST` | `/api/v1/appointments/{appointment_id}/cancel` | Authenticated | Cancel scheduled appointment | `200 OK` |
| `POST` | `/api/v1/appointments/{appointment_id}/complete` | Admin / Staff / Doctor | Mark appointment completed | `200 OK` |
| `POST` | `/api/v1/documents/upload` | Clinical Roles | Upload medical document (PDF, DOCX, TXT) | `201 Created` |
| `GET` | `/api/v1/documents/{document_id}` | Clinical Roles | Get document metadata & processing status | `200 OK` |
| `GET` | `/api/v1/documents/patient/{patient_id}` | Clinical Roles | List documents for a patient | `200 OK` |
| `POST` | `/api/v1/rag/query` | Authenticated | Execute grounded clinical RAG query | `200 OK` |
| `POST` | `/api/v1/chat/sessions` | Authenticated | Create a new clinical chat session | `201 Created` |
| `POST` | `/api/v1/chat/sessions/{session_id}/messages` | Authenticated | Send message in session (grounded RAG) | `200 OK` |
| `GET` | `/api/v1/chat/sessions/{session_id}/stream` | Authenticated | SSE streaming clinical chat response | `200 OK` |
| `GET` | `/api/v1/timeline/{patient_id}` | Clinical Roles | Get aggregated chronological timeline | `200 OK` |
| `GET` | `/api/v1/timeline/{patient_id}/summary` | Clinical Roles | Get RAG-grounded longitudinal summary | `200 OK` |
| `POST` | `/api/v1/safety/check` | Clinical Roles | Run clinical safety check (meds/allergies/DDIs) | `200 OK` |
| `GET` | `/api/v1/fhir/Patient/{patient_id}` | Authenticated | Export patient demographics as FHIR R4 Patient | `200 OK` |
| `GET` | `/api/v1/fhir/Encounter/{encounter_id}` | Authenticated | Export encounter as FHIR R4 Encounter | `200 OK` |
| `GET` | `/api/v1/fhir/Condition/{condition_id}` | Authenticated | Export diagnosis as FHIR R4 Condition | `200 OK` |
| `GET` | `/api/v1/fhir/MedicationStatement/{medication_id}` | Authenticated | Export medication history as FHIR R4 MedicationStatement | `200 OK` |
| `GET` | `/api/v1/fhir/Observation/{observation_id}` | Authenticated | Export observation findings as FHIR R4 Observation | `200 OK` |
| `GET` | `/api/v1/fhir/patients/{patient_id}/bundle` | Authenticated | Export patient history as FHIR R4 collection Bundle | `200 OK` |
| `POST` | `/api/v1/fhir/import` | Clinical Roles | Ingest and persist a single FHIR R4 resource | `200 OK` |
| `POST` | `/api/v1/fhir/Bundle` | Clinical Roles | Batch ingest multiple resources from FHIR R4 Bundle | `200 OK` |
| `POST` | `/api/v1/tasks/documents/{document_id}/process` | Clinical Roles | Enqueue background document extraction & vector indexing | `202 Accepted` |
| `POST` | `/api/v1/tasks/timeline/{patient_id}/summary` | Clinical Roles | Enqueue background longitudinal timeline summary compilation | `202 Accepted` |
| `GET` | `/api/v1/tasks/{task_id}` | Authenticated | Retrieve background task status, progress, and results | `200 OK` |
| `GET` | `/api/v1/tasks` | Authenticated | List authorized background tasks with filtering & pagination | `200 OK` |
| `POST` | `/api/v1/tasks/{task_id}/retry` | Clinical Roles | Re-enqueue a failed or cancelled background task | `200 OK` |
| `POST` | `/api/v1/tasks/{task_id}/cancel` | Clinical Roles | Cancel a pending background task | `200 OK` |
| `GET` | `/health` | Public | Lightweight application liveness probe | `200 OK` |
| `GET` | `/ready` | Public | Core readiness probe verifying database connectivity | `200 OK` |
| `GET` | `/api/v1/health/live` | Public | API liveness probe with correlation ID | `200 OK` |
| `GET` | `/api/v1/health/ready` | Public | Deep dependency readiness probe (database, vector store, task workers) | `200 OK` |
| `GET` | `/api/v1/health/metrics` | Public | In-memory operational metrics snapshot (latency, errors, task queues) | `200 OK` |
| `GET` | `/docs` | Public | OpenAPI / Swagger Documentation | `200 OK` |
| `GET` | `/redoc` | Public | ReDoc API Documentation | `200 OK` |

---

## 🗺️ Project Roadmap & Planned Milestones

1. **Milestone 1: Backend Foundation** *(Completed & Pushed)* ✅
2. **Milestone 2: Database Layer & Relational Modeling** *(Completed & Pushed)* ✅
3. **Milestone 3: Authentication & Role-Based Access Control** *(Completed & Pushed)* ✅
4. **Milestone 4: Patient Management** *(Completed & Pushed)* ✅
5. **Milestone 5: Medical Records & Clinical Encounters** *(Completed & Pushed)* ✅
6. **Milestone 6: Doctor Management & Department Discovery** *(Completed & Verified)* ✅
7. **Milestone 7: Appointment Scheduling & Care Team Allocation** *(Completed & Verified)* ✅
8. **Milestone 8: Clinical AI, RAG & Clinical Intelligence** *(Completed & Verified)* ✅
9. **Milestone 9: Healthcare Interoperability & Operational Reliability**
   - **Phase 9.0.1 — FHIR R4 Ingestion & Interoperability**: Completed & Verified ✅
   - **Phase 9.0.2 — Authoritative Drug Knowledge Base Adapter**: Completed & Verified ✅
   - **Phase 9.0.3 — Background Asynchronous Worker Architecture**: Completed & Verified ✅
   - **Phase 9.0.4 — Production Observability, Reliability & Operational Monitoring**: Completed & Verified ✅

### Next — Planned Future Work (Roadmap Only)

- **Phase 9.0.5 — Advanced Production Deployment & Scalability**:
  - Container orchestration & horizontal scaling architectures
  - Production distributed worker topologies & cluster caching
  - Distributed tracing (OpenTelemetry integration points)
  - Real-time WebSocket task progress streaming
  - Frontend clinical decision support & task monitoring UI
