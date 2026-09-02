# MediGen-AI: Clinical Decision Support System & FHIR-Native EHR Platform

[![CI Pipeline](https://github.com/Harish2004-sonwale/MediGen-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/Harish2004-sonwale/MediGen-AI/actions)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![TypeScript 5](https://img.shields.io/badge/TypeScript-5+-3178C6.svg)](https://www.typescriptlang.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![HL7 FHIR R4](https://img.shields.io/badge/HL7-FHIR%20R4-orange.svg)](https://hl7.org/fhir/)
[![DICOM PS3.18](https://img.shields.io/badge/DICOM-PS3.18%20Web-blueviolet.svg)](https://www.dicomstandard.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 What It Is

**MediGen-AI** is an enterprise-grade Clinical Decision Support System (CDSS) and Electronic Health Record (EHR) platform engineered to modernize clinical workflows, enforce bedside medication administration safety, support multi-modal diagnostic imaging (DICOM PACS) and real-time ICU physiological waveform telemetry (12-Lead ECG), and provide grounded, citation-backed clinical intelligence.

---

## ⚕️ Healthcare Safety & Assistive Disclaimer

> [!IMPORTANT]
> **MediGen-AI is designed strictly as an assistive clinical decision support and educational/demonstration platform.**
> All AI-generated outputs, analyses, summaries, and suggestions must undergo review and verification by certified healthcare professionals before any clinical application or treatment decision. MediGen-AI does not provide standalone diagnostic determinations or replace professional medical judgment. This software has not been independently certified by regulatory bodies (e.g., FDA, CE-MDR) for autonomous clinical deployment.

---

## 🌟 Core Capabilities

### 1. Clinical EHR & Patient Management
- **Master Patient Index**: Demographic records, MRN indexing, active clinical problem lists, allergy banners, and encounter timelines.
- **Clinical Encounters & Notes**: Structured SOAP note authoring, clinician electronic signing, and AI Scribe audio transcription simulation.
- **Transitions of Care**: Multi-disciplinary clinical handoffs implementing standardized I-PASS and SBAR communication frameworks.

### 2. Medication Safety & CPOE
- **Closed-Loop Barcode Medication Administration (BCMA / eMAR)**: Bedside optical barcode verification enforcing the 5 Rights (Right Patient, Right Drug NDC, Right Dose, Right Route, Right Time).
- **ISMP High-Alert Safeguards**: Mandatory dual-clinician witness authentication modal before administering high-alert medications.
- **CPOE & Order Sets**: Multidisciplinary protocol bundles (Sepsis, DKA, Stroke, ACS) with proactive Drug-Drug and Drug-Allergy interaction checks.
- **Pharmacogenomics (CPIC)**: Real-time Level A/B gene-drug interaction guidance (*CYP2C19*, *CYP2D6*, *SLCO1B1*).

### 3. Diagnostic Imaging (PACS) & ICU Waveform Telemetry
- **Interactive DICOM PACS Viewer**: HTML5 Canvas renderer with DICOM PS3.18 QIDO-RS/WADO-RS queries, client-side Window/Level transfer functions (Soft Tissue, Lung, Bone, Brain, Stroke), zoom/pan, millimeter calipers, and radiologist AI lesion confirm/reject workflows.
- **12-Lead Continuous ECG Monitor**: 250 Hz continuous multi-lead physiological waveform streaming (Leads I-III, aVR-aVF, V1-V6) with real-time arrhythmia detection (STEMI, AFib with RVR, V-Tach, Asystole) and debounced alarm acknowledgment.

### 4. Healthcare Interoperability & Standards
- **HL7 FHIR Release 4**: Bidirectional resource mapping for `Patient`, `Encounter`, `Condition`, `Observation`, `MedicationRequest`, `DiagnosticReport`, and `CarePlan`.
- **SMART on FHIR 2.0**: OAuth2 PKCE authorization server with granular scope enforcement (`patient/*.read`, `user/*.*`).
- **Bulk FHIR ($export)**: Multi-resource NDJSON streaming export engine honoring patient consent opt-outs.
- **Enterprise Master Patient Index (EMPI)**: Probabilistic and deterministic demographic patient linkage engine.

### 5. Grounded Clinical AI & Autonomous Agents
- **Retrieval-Augmented Generation (RAG)**: ChromaDB vector search with verifiable source document citations and chunk similarity scores.
- **Autonomous Multi-Agent Orchestrator**: Multi-agent clinical coordination across Triage, Safety Guardian, Clinical Pharmacist, and Care Coordinator agents.

### 6. Security, Governance & Observability
- **Multi-Tenant & Multi-Facility Isolation**: Scoped clinical queries with `X-Facility-ID` routing and cross-facility transfer authorization.
- **Tamper-Evident Audit Logging**: Cryptographic HMAC-SHA256 chained audit logs.
- **OpenTelemetry & Prometheus**: W3C `traceparent` distributed tracing and `/api/v1/health/metrics/prometheus` metrics exporter.

---

## 🏗️ System Architecture

```
[ Web & Mobile Clients ]
  React 18 + TypeScript SPA | HTML5 Canvas DICOM Viewer | 12-Lead ECG Strip Player
         │
         │  HTTPS / WSS (W3C traceparent, X-Facility-ID, JWT Bearer)
         ▼
[ Ingress Reverse Proxy ]
  Nginx 1.27 Edge Gateway | TLS Termination | Security Headers (CSP, HSTS, X-Frame-Options)
         │
         ▼
[ MediGen-AI FastAPI Application ]
  ├── Middleware: CorrelationIdMiddleware, SecurityHeadersMiddleware, RateLimiterMiddleware
  ├── Routers: /auth, /patients, /encounters, /orders, /emar, /cds, /pacs, /waveforms, /fhir
  ├── Background Workers: Transactional Outbox Engine, Celery / Local Worker Pool
  └── AI Subsystem: ChromaDB Vector Store, Grounded Citation Engine, Multi-Agent Orchestrator
         │
         ▼
[ Persistence & Cache Tier ]
  PostgreSQL 14+ (SQLAlchemy 2.0, Alembic) | SQLite (Dev/Demo) | Redis 7 (Cache/PubSub)
```

---

## 🚀 Quick Start (Local Demo)

### Prerequisites
- **Python 3.11+**
- **Node.js 20+** and **npm**
- **Git**

### Step 1: Clone Repository
```bash
git clone https://github.com/Harish2004-sonwale/MediGen-AI.git
cd MediGen-AI
```

### Step 2: Configure Environment
Copy `.env.example` to `backend/.env`:
```bash
cp .env.example backend/.env
```
*(Default settings use SQLite and in-memory providers for zero-dependency instant startup).*

### Step 3: Start Backend
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Backend will be available at `http://127.0.0.1:8000` (Swagger UI: `http://127.0.0.1:8000/docs`).

### Step 4: Start Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```
Frontend will be available at `http://localhost:3000`.

### Step 5: Demo Login Credentials

| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@hospital.org` | `AdminPassword123!` |
| **Doctor** | `doctor@hospital.org` | `DoctorPassword123!` |
| **Patient** | `patient@hospital.org` | `PatientPassword123!` |

---

## 🐳 Docker Deployment (Production Stack)

To run the complete production multi-container stack (Nginx Ingress, React Frontend, FastAPI Backend, PostgreSQL 14, and Redis 7):

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Check service health:
```bash
docker compose -f docker-compose.prod.yml ps
```

Access:
- **Application Ingress**: `http://localhost`
- **Backend API**: `http://localhost/api/v1/health/ready`
- **Prometheus Metrics**: `http://localhost/api/v1/health/metrics/prometheus`

---

## 🧪 Automated Test & Verification Metrics

All automated continuous integration suites are 100% green across GitHub Actions:

| Suite | Verified Metrics |
|---|---|
| **Backend (pytest)** | **514 passed, 3 skipped, 0 failed** (100% pass rate) |
| **Frontend (Vitest)** | **93 passed across 29 test files** (100% pass rate) |
| **TypeScript (`tsc`)** | **0 errors** (`npx tsc --noEmit`) |
| **Production Bundle** | **✓ built in 3.68s** (`npm run build`) |
| **Security (Bandit)** | **0 High, 0 Medium issues** across 47,371 lines of code |
| **Linter (Flake8)** | **0 errors** |
| **Alembic Migrations** | **Valid SQL up to Head 0029** (`alembic upgrade head --sql`) |
| **E2E Platform Smoke** | **16/16 stages verified PASS** |
| **Docker Build** | **Clean multi-stage non-root container builds** |

---

## ⚙️ External Dependencies & Configuration

The application operates out-of-the-box in local demonstration mode. For live production environments, configure the following optional integrations in `.env`:

- **Redis**: Set `REDIS_URL` for distributed multi-node caching and Celery task queues.
- **Cloud LLM APIs**: Set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY` for live generative AI models.
- **Speech Transcription**: Set `SPEECH_PROVIDER="whisper"` and `OPENAI_WHISPER_API_KEY` for live audio AI Scribe.
- **Hospital PACS**: Configure `DICOM_PACS_HOST` and `DICOM_PACS_PORT` to connect with external Orthanc or DCM4CHEE DICOM servers.

---

## 📚 Documentation Index

- [System Architecture](docs/architecture.md)
- [Live Demonstration Script (5-10 min)](docs/demo_script.md)
- [Engineering Portfolio Summary](docs/portfolio_summary.md)
- [Visual Screenshot Capture Plan](docs/screenshot_plan.md)
- [Production Readiness Checklist](docs/production_readiness_checklist.md)
- [Final Product Audit Report](docs/final_product_audit.md)
- [Project Roadmap](docs/remaining_project_roadmap.md)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
