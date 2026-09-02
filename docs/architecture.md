# MediGen-AI Architecture Design Document

## 1. System Overview

MediGen-AI is a high-availability, multi-tenant Clinical Decision Support System (CDSS) and Electronic Health Record (EHR) platform engineered to support modern hospital clinical workflows, healthcare interoperability (HL7 FHIR R4, SMART on FHIR 2.0, DICOM PS3.18, C-CDA), bedside medication administration safety (BCMA/eMAR), multi-modal diagnostic imaging, real-time ICU physiological waveform telemetry, and grounded retrieval-augmented clinical AI.

```
+-----------------------------------------------------------------------------------+
|                            Client Tier (Web & Mobile)                            |
|  React 18 + TypeScript SPA | Vite | DICOM HTML5 PACS Viewer | ECG Waveform Strip  |
+-----------------------------------------+-----------------------------------------+
                                          | HTTPS / WebSockets (W3C traceparent, X-Facility-ID)
                                          v
+-----------------------------------------------------------------------------------+
|                        Ingress & Edge Security Layer                              |
|   Nginx 1.27 Reverse Proxy | TLS Termination | CSP / HSTS / X-Frame-Options       |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        MediGen-AI FastAPI ASGI Application                        |
|                                                                                   |
|  [Middleware Stack]                                                               |
|  - CorrelationIdMiddleware (W3C traceparent context & request timing)             |
|  - SecurityHeadersMiddleware (nosniff, DENY, strict-origin, camera=())            |
|  - RateLimiterMiddleware (Sliding-window tiered IP/User rate limiting)           |
|  - CORSMiddleware (Configurable origin validation & wildcard rejection)           |
|                                                                                   |
|  [Clinical API Routers (/api/v1)]                                                 |
|  - Auth & MFA (/auth)            - Patients (/patients)      - Encounters (/enc)  |
|  - CPOE Orders (/orders)         - eMAR & BCMA (/emar)       - CDS & PGx (/cds)   |
|  - DICOM PACS (/pacs)            - ECG Waveforms (/waveforms)- FHIR R4 (/fhir)   |
|  - Clinical Trials (/trials)     - Telehealth & RTC (/ws)    - Health/Ready/Prom  |
+-------------------+---------------------+--------------------+--------------------+
                    |                     |                    |
                    v                     v                    v
+-------------------+---+  +--------------+---+  +-------------+--------------------+
|  Persistence Tier     |  | Background Worker|  | Clinical AI & RAG Subsystem      |
|  - PostgreSQL 14+     |  | - Transactional  |  | - ChromaDB Ephemeral Vector Store|
|    (SQLAlchemy 2.0,   |  |   Outbox Engine  |  | - Deterministic Embedding &      |
|     Alembic Head 0029)|  | - Celery / Local |  |   Clinical LLM Abstraction Layer|
|  - SQLite (Dev/Demo)  |  |   Worker Pool    |  | - Multi-Agent Coordinator        |
|  - Redis Cache & PubSub  | - Scheduled Beat |  | - Grounded Citation Synthesizer  |
+-----------------------+  +------------------+  +----------------------------------+
```

---

## 2. Frontend Architecture

- **Technology**: React 18, TypeScript 5, Vite 5, TailwindCSS utility styling.
- **State & Context Management**:
  - `AuthContext`: Manages JWT access tokens, active clinician identity, user roles (`Admin`, `Doctor`, `Patient`), and logout workflows.
  - `FacilityContext`: Manages active health facility scope (`FAC-METRO-MAIN`, `FAC-METRO-WEST`) and injects `X-Facility-ID` headers into all outbound API calls.
  - `PatientContext`: Tracks selected active patient context across clinical workspaces.
- **Diagnostic Canvas Components**:
  - `DICOMPACSViewer`: High-performance HTML5 Canvas renderer supporting Window/Level adjustments, pan/zoom transformation matrices, inversion, millimeter distance calipers, and AI lesion bounding box overlays.
  - `ECGWaveformPlayer`: Multi-lead continuous strip renderer drawing 12 simultaneous physiological leads (I, II, III, aVR, aVL, aVF, V1-V6) at 250 Hz with real-time sweep bar animation and alarm acknowledgments.
  - `BCMAScanner`: Bedside optical barcode emulation verifying 5-rights matching with ISMP dual-witness modal authentication.

---

## 3. Backend Architecture

- **Framework**: FastAPI (ASGI) built on Starlette and Pydantic v2.
- **Database Layer**: SQLAlchemy 2.0 with connection pooling (`pool_pre_ping=True`, configurable pool sizes, statements timeouts, and recycling) and Alembic migration tracking.
- **Security & Middleware Stack**:
  1. `CorrelationIdMiddleware`: Extracts or generates `req-YYYYMMDD-HEX` correlation IDs and parses/propagates standard W3C `traceparent` headers (`00-{trace_id}-{span_id}-01`).
  2. `SecurityHeadersMiddleware`: Enforces `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, HSTS, and CSP.
  3. `RateLimiterMiddleware`: In-memory sliding-window token bucket limiter enforcing strict tiers (5 req/min on `/auth/login`, 20 req/min on `/rag/query`, 15 req/min on `/fhir/patients/.../bundle`, 60 req/min default).
  4. `CORSMiddleware`: Strict origin validation rejecting insecure wildcard configurations in production.

---

## 4. Authentication, RBAC & Multi-Tenancy

- **Authentication Protocol**: OAuth2 Password Grant returning HMAC-SHA256 JWT access tokens.
- **Role-Based Access Control (RBAC)**:
  - `Admin`: Tenant governance, system audit chain verification, facility management.
  - `Doctor`: Patient management, clinical encounter authoring, CPOE order placement, PACS AI review, and note signing.
  - `Patient`: Scoped access restricted strictly to own clinical data, observations, and telehealth portals.
- **Multi-Tenant / Multi-Facility Isolation**:
  - Records partition across tenants and clinical facilities (`clinical_facilities`).
  - Active facility header `X-Facility-ID` enforced on all patient queries and clinical actions.
  - Cross-facility patient record access requires explicit transfer authorization and clinical hold checks.

---

## 5. Clinical Domain Modules

- **Patient Lifecycle**: Demographic records, MRN indexing, allergy tracking, problem lists, and active status flags.
- **Clinical Encounters & Notes**: SOAP note composition, clinician electronic signatures, and AI Scribe audio transcription synthesis.
- **CPOE Orders & CDS**: Order entry for medications, labs, imaging, and consults with real-time Drug-Drug / Drug-Allergy interaction checking and multidisciplinary order set bundles (Sepsis, DKA, Stroke, ACS).
- **Medication Administration (eMAR / BCMA)**: 5-Rights bedside barcode scanning engine (Right Patient, Right Medication, Right Dose, Right Route, Right Time) with ISMP high-alert dual sign-off.
- **Pharmacogenomics (CPIC)**: Level A/B gene-drug interaction guidelines (e.g. *CYP2C19* / Clopidogrel, *CYP2D6* / Codeine, *SLCO1B1* / Simvastatin).
- **Clinical Trials Matching**: Automated biomarker-driven clinical trial matching engine with GCP protocol deviation tracking.
- **Quality Measures & Care Gaps**: CMS / HEDIS compliance scoring (CMS122 Diabetes HbA1c, CMS165 Hypertension Control, CMS130 Colorectal Cancer Screening) with automated care task dispatch.

---

## 6. Imaging PACS & Physiological Waveforms

- **DICOM PACS Architecture**:
  - Standards: DICOM PS3.18 Web Services (QIDO-RS for study search, WADO-RS for metadata and instance retrieval).
  - Data Hierarchy: `Study` $\rightarrow$ `Series` $\rightarrow$ `Instance` $\rightarrow$ `AILesionFinding`.
  - Radiologist AI Review: Lesion findings store coordinates, bounding box geometry, confidence scores, and clinician confirm/reject review status.
- **12-Lead Continuous ICU Waveforms**:
  - Ingestion: 250 Hz sample rate across standard 12 leads (I, II, III, aVR, aVL, aVF, V1-V6).
  - Arrhythmia Detection: Automated real-time detection for STEMI ST-elevation, Atrial Fibrillation with RVR, Ventricular Tachycardia, and Asystole.
  - Debouncing: 5-minute automated alert cooldown per patient session with mandatory clinician action audit logging upon acknowledgment.

---

## 7. Healthcare Interoperability & Standards

- **HL7 FHIR Release 4**: Full FHIR JSON resource mapping for `Patient`, `Encounter`, `Condition`, `Observation`, `MedicationRequest`, `DiagnosticReport`, and `CarePlan`.
- **SMART on FHIR 2.0**: OAuth2 authorization server with PKCE and granular scopes (`patient/*.read`, `user/*.*`, `launch/patient`).
- **Bulk FHIR ($export)**: Multi-resource NDJSON streaming export engine with patient consent opt-out enforcement.
- **Enterprise Master Patient Index (EMPI)**: Deterministic and probabilistic patient demographic linkage engine.
- **C-CDA R2.1**: Clinical Document Architecture XML generation and ingestion.

---

## 8. Clinical AI & Grounded RAG Subsystem

- **Grounded Retrieval-Augmented Generation (RAG)**:
  - Vector Store: ChromaDB with ephemeral in-memory isolation for testing and persistent collection storage for production.
  - Embeddings: Pluggable provider interface (default deterministic mock provider for zero-dependency operation; OpenAI/Anthropic/Gemini compatible).
  - Groundedness Guarantee: Direct citations linked to source clinical document chunks with similarity scores and page numbers.
- **Autonomous Multi-Agent Coordination**:
  - Multi-agent orchestrator executing clinical workflows across Triage Agent, Safety Guardian, Clinical Pharmacist, and Care Coordinator.

---

## 9. Reliability, Observability & Security

- **Transactional Outbox Engine**: Outbox event table guaranteeing at-least-once asynchronous event delivery and WebSocket fanout.
- **Tamper-Evident Audit Logging**: HMAC-SHA256 chained audit logs with cryptographic tamper detection.
- **Prometheus Metrics**: Standard `/api/v1/health/metrics/prometheus` exporter publishing request latency histograms, database connection pool gauges, cache status, and AI inference counts.
- **Distributed Tracing**: Standard W3C `traceparent` context propagation across all requests and background worker tasks.

---

## 10. Container & Deployment Architecture

- **Ingress**: Alpine-based Nginx 1.27 reverse proxy with healthcheck routing.
- **Frontend Container**: Multi-stage `node:20-alpine` build deployed on optimized `nginx:alpine`.
- **API Container**: Multi-stage non-root `python:3.11-slim` container executing Uvicorn with ASGI worker tuning.
- **Database Container**: Hardened `postgres:14-alpine` with healthcheck probes.
- **Cache Container**: `redis:7-alpine` with persistent volume mounts.
