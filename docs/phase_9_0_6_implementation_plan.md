# Phase 9.0.6 Implementation Plan — Frontend Clinical Dashboard & Real-Time Decision Support UI

## 1. Current Architecture
MediGen AI possesses a comprehensive, fully tested FastAPI backend with:
- PostgreSQL 16 relational storage (Alembic migrations 0001–0008).
- Role-Based Access Control (`admin`, `doctor`, `healthcare_staff`, `patient`).
- Patient data isolation and care team security.
- Clinical RAG knowledge retrieval and multi-turn conversational AI.
- SSE (Server-Sent Events) streaming chat (`POST /api/v1/chat/sessions/{session_id}/messages/stream`).
- Longitudinal clinical timeline aggregation and AI narrative summary.
- Clinical Decision Support (CDS) safety checks (drug-drug interactions, allergies, duplications, contraindications).
- FHIR R4 ingestion and export capabilities (Patient, Encounter, Condition, MedicationStatement, Observation, Bundle).
- Background asynchronous tasks (OCR, indexing, timeline compilation).
- Observability and deep readiness probes (`/ready`, `/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/health/metrics`).

---

## 2. Existing Frontend Status
- `frontend/` directory is currently **empty**.
- No Node/React/Next.js files or `package.json` currently exist in the repository.
- Backend CORS configuration is already configured to support frontend development (`*` in dev, explicit domains in prod).

---

## 3. Verified Backend API Contracts

| API Module | Endpoint & Method | Request Schema | Response Schema | Access / RBAC |
|---|---|---|---|---|
| **Auth** | `POST /api/v1/auth/login` | `UserLoginRequest` (`email`, `password`) | `TokenResponse` (`access_token`, `token_type`, `user`) | Public |
| **Auth** | `POST /api/v1/auth/register` | `UserRegisterRequest` (`name`, `email`, `password`, `role`) | `UserResponse` (`id`, `name`, `email`, `role`, `is_active`) | Public |
| **Auth** | `GET /api/v1/auth/me` | None (Bearer token) | `UserResponse` | Authenticated |
| **Patients** | `GET /api/v1/patients` | Query: `skip`, `limit`, `search`, `status` | `list[PatientResponse]` | Doctor, Staff, Admin |
| **Patients** | `GET /api/v1/patients/{patient_id}` | Path: `patient_id` | `PatientResponse` | Clinical Roles or Own Patient |
| **Patients** | `POST /api/v1/patients` | `PatientCreate` | `PatientResponse` | Doctor, Staff, Admin |
| **Timeline** | `GET /api/v1/patients/{patient_id}/timeline` | Query: `event_type`, `start_date`, `end_date`, `skip`, `limit` | `list[TimelineEventResponse]` | Clinical Roles or Own Patient |
| **Timeline** | `GET /api/v1/patients/{patient_id}/timeline/summary` | Query: `focus` | `TimelineSummaryResponse` (`summary`, `citations`, `total_events_analyzed`) | Clinical Roles or Own Patient |
| **Chat** | `POST /api/v1/chat/sessions` | `ChatSessionCreate` (`patient_id`, `title`) | `ChatSessionResponse` | Clinical Roles or Own Patient |
| **Chat** | `GET /api/v1/chat/sessions` | Query: `patient_id` | `ChatSessionListResponse` | Clinical Roles or Own Patient |
| **Chat** | `GET /api/v1/chat/sessions/{session_id}` | Path: `session_id` | `ChatSessionDetailResponse` | Clinical Roles or Own Patient |
| **Chat** | `POST /api/v1/chat/sessions/{session_id}/messages/stream` | `ChatMessageCreate` (`message`, `top_k`, `min_similarity`) | SSE Event Stream | Clinical Roles or Own Patient |
| **Safety** | `POST /api/v1/safety/check?patient_id={patient_id}` | `SafetyCheckRequest` (`candidate_medications`, `active_conditions`) | `ClinicalSafetyReport` (`alerts`, `safe_to_proceed`, `summary`, `disclaimer`) | Clinical Roles or Own Patient |
| **Documents** | `GET /api/v1/patients/{patient_id}/documents` | Query: `skip`, `limit` | `list[MedicalDocumentResponse]` | Clinical Roles or Own Patient |
| **Documents** | `POST /api/v1/patients/{patient_id}/documents` | Multipart Form: `file`, `title`, `document_type` | `MedicalDocumentResponse` | Doctor, Staff, Admin |
| **Tasks** | `GET /api/v1/tasks` | Query: `task_type`, `status`, `patient_id`, `page`, `size` | `TaskListResponse` (`items`, `total`, `page`, `size`) | Authenticated |
| **Tasks** | `GET /api/v1/tasks/{task_id}` | Path: `task_id` | `BackgroundTaskResponse` | Authenticated |
| **Tasks** | `POST /api/v1/tasks/{task_id}/retry` | Path: `task_id` | `BackgroundTaskResponse` | Doctor, Staff, Admin |
| **Tasks** | `POST /api/v1/tasks/{task_id}/cancel` | Path: `task_id` | `BackgroundTaskResponse` | Doctor, Staff, Admin |
| **FHIR** | `GET /api/v1/fhir/patients/{patient_id}/bundle` | Path: `patient_id` | FHIR R4 `Bundle` JSON | Clinical Roles or Own Patient |
| **FHIR** | `POST /api/v1/fhir/Bundle` | FHIR R4 `Bundle` JSON | Import confirmation summary | Doctor, Staff, Admin |
| **Health** | `GET /api/v1/health/ready` | None | `ReadinessResponse` (`components`, `status`) | Public |
| **Health** | `GET /api/v1/health/metrics` | None | `MetricsResponse` (`http`, `tasks`, `uptime_seconds`) | Public |

---

## 4. Proposed Frontend Architecture
- **Framework**: React 18 + Vite + TypeScript.
- **Styling**: Vanilla CSS with modern clinical design tokens (Glassmorphism, dark/light theme, accessible healthcare HSL palette).
- **Routing**: `react-router-dom` v6 with RBAC protected route wrappers.
- **State Management**: React Context (`AuthContext`, `PatientContext`, `TaskContext`) + custom hooks (`useStreamingChat`, `useTimeline`, `useSafetyCheck`).
- **HTTP Client**: Typed fetch wrapper with automatic JWT injection, 401 token expiry handling, and `X-Correlation-ID` tracking.

---

## 5. Scope Breakdown

### 5.1 MVP Core Features
1. **Authentication & Role Switching**:
   - Clean login with demo credentials prefill (Doctor, Admin, Staff, Patient).
   - Session preservation and auto-token refresh handling.
2. **Patient Directory & Active Context Bar**:
   - Searchable patient list with demographics, status badges, and quick-select.
   - Persistent active patient bar across clinical views.
3. **Longitudinal Clinical Timeline**:
   - Interactive chronological timeline (encounters, documents, appointments).
   - AI longitudinal summary card with grounded document citations.
4. **Real-Time Clinical AI Copilot**:
   - Multi-turn conversational interface.
   - SSE streaming token rendering (`start`, `delta`, `citation`, `done`, `error`).
   - Clickable citation reference badges with excerpt popovers.
5. **Clinical Decision Support (CDS) Prescriber**:
   - Pre-prescription safety modal with candidate drug entry.
   - Color-coded alert cards (Contraindications, Drug Interactions, Allergies, Duplications).
   - Safe-to-proceed indicator and clinical review acknowledgment.
6. **Medical Document Hub & Task Progress**:
   - Document upload dropzone (PDF/DOCX).
   - Live background task progress bar and status polling.

### 5.2 Secondary / Optional Features
1. **FHIR R4 Interoperability Center**:
   - Export patient bundle as formatted FHIR JSON.
   - Batch bundle import wizard.
2. **System Health & Observability Widget**:
   - Live dependency status indicator (Database, Vector Store, Task Workers).
   - Operational metrics snapshot.

---

## 6. SSE Streaming Chat Architecture
The frontend `useStreamingChat` hook consumes the backend SSE stream:
- `event: start` $\rightarrow$ Initializes assistant bubble with `session_id` and `message_id`.
- `event: delta` $\rightarrow$ Appends token deltas in real-time to streaming message buffer.
- `event: citation` $\rightarrow$ Accumulates structured citation metadata (`title`, `page_number`, `document_id`, `document_type`).
- `event: done` $\rightarrow$ Marks turn complete and renders citation badges.
- `event: error` $\rightarrow$ Displays inline error message with retry button.

---

## 7. Task-Status Polling Architecture
- Submitting background work (e.g. document OCR or timeline compilation) returns HTTP 202 with `task_id`.
- `useTaskManager` hook polls `GET /api/v1/tasks/{task_id}` every 2000ms until `completed` or `failed`.
- Real-time progress bar reflects `task.progress * 100`%.
- Failed tasks render a 1-click **Retry Task** button invoking `POST /api/v1/tasks/{task_id}/retry`.

---

## 8. Security Controls
- **Zero Secrets in Frontend**: All LLM keys, Bedrock credentials, and DB strings remain exclusively on backend.
- **Client Token Storage**: JWT stored in `sessionStorage` with validation against `exp` timestamp.
- **Strict Patient Isolation**: UI patient context is passed as a query/path parameter, and backend RBAC strictly enforces ownership.

---

## 9. Testing Strategy
- **Frontend Unit & Component Tests**: Vitest + React Testing Library (mocking API responses).
- **Key test cases**:
  - Auth context login / logout / token preservation.
  - Protected route redirection for unauthorized roles.
  - Streaming chat chunk accumulation and citation rendering.
  - Safety alert color-coding and override validation.
  - Timeline chronological sorting and filter updates.
- **Backend Regression Suite**: Existing 315 tests must remain 100% passing.

---

## 10. Step-by-Step Implementation Order
1. Setup Vite + React + TypeScript in `frontend/`.
2. Configure CSS design tokens, typography, and base theme.
3. Build API client layer with typed models.
4. Implement `AuthContext` and Login / Registration views.
5. Build navigation layout and RBAC protected routing.
6. Build Patient Directory and Patient Context Provider.
7. Build Longitudinal Timeline & AI Summary view.
8. Build Real-Time SSE Streaming Chat Copilot with citation popovers.
9. Build Clinical Decision Support (CDS) Safety prescriber modal.
10. Build Document Hub and Background Task Monitor.
11. Build FHIR Interoperability Center & System Diagnostics.
12. Run frontend test suite & full backend regression suite.
13. Finalize documentation, commit, and push.
