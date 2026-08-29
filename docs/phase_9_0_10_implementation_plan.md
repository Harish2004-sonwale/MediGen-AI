# Phase 9.0.10 Implementation Plan — Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management

## 1. Phase Title & Objectives
**Phase 9.0.10 — Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management**

### 1.1 Objective
To design and implement a comprehensive, clinically safe, and audit-compliant Clinical Workflow Orchestration and Care Coordination engine for MediGen AI. This phase bridges clinical encounters, AI scribe notes, medical imaging findings, and real-time vital alerts into actionable, patient-specific Care Plans with structured health goals, scheduled clinical interventions, assignable follow-up tasks, appointment coordination, and FHIR R4 `CarePlan` & `Task` interoperability.

---

## 2. Current Architecture Findings & Repository Inspection
Inspection of the existing MediGen AI repository reveals:
- **Core Entities**: `Patient`, `Doctor`, `Encounter`, `Appointment`, `MedicalDocument`, `DiagnosticMedia`, `ClinicalNote`, `VitalTelemetry`, `ClinicalAlert`.
- **AI & RAG Engine**: Longitudinal RAG vector store, clinical safety engine, multi-modal imaging mock provider, and clinical scribe note synthesis provider.
- **Background Worker Infrastructure**: `BaseBackgroundTaskProvider` with `SyncBackgroundTaskProvider`, `LocalBackgroundTaskProvider`, and `CeleryBackgroundTaskProvider` handling `document_processing`, `timeline_summary`, `safety_check`, `batch_indexing`, `media_analysis`, `note_synthesis`, and `telemetry_evaluation`.
- **Database Schema**: 11 completed Alembic migrations (`0001_initial_schema` through `0011_vitals_and_clinical_alerts`).
- **Frontend Architecture**: React 18 + Vite + TypeScript dashboard with tabs for Chat, Timeline, Documents, Imaging, Notes, and Vitals & CDS Alerts.

---

## 3. Existing Functionality to Reuse (No Duplication)
1. **Patient & Encounter Models**: Care plans and tasks will link directly to existing `patients.id` and `encounters.id`.
2. **Doctor & User Models**: Task assignment and care plan authorship will reference `doctors.id` and `users.id`.
3. **Appointment Scheduling**: Follow-up tasks will optionally reference `appointments.id` to establish seamless scheduling handoffs.
4. **Clinical Context Ingestion**: AI Care Plan Synthesis will aggregate data from existing models (`MedicalDocument`, `ClinicalNote`, `DiagnosticMedia`, `VitalTelemetry`, `ClinicalAlert`) without re-implementing data access.
5. **Background Task Framework**: We will add `BackgroundTaskType.CARE_PLAN_GENERATION = "care_plan_generation"` to existing queue mechanisms.
6. **FHIR Foundation**: We will extend `FHIRService` with R4 `CarePlan`, `Goal`, and `Task` mappings.

---

## 4. Features to Implement

### 4.1 Structured Clinical Care Plans (`CarePlan`)
- **Category / Domain**: `chronic_disease_management`, `post_discharge_followup`, `preventive_care`, `rehabilitation`, `acute_care_plan`.
- **Status Lifecycle**: `draft` -> `reviewed` -> `active` -> `completed` / `suspended` / `cancelled`.
- **Goals (`goals_json`)**: Structured clinical targets with target date, baseline value, and target metric (e.g. `Target Systolic BP < 130 mmHg`, `Target HbA1c < 7.0%`).
- **Interventions (`interventions_json`)**: Structured activities (e.g. medication adjustment, daily home telemetry monitoring, dietary counseling, physical therapy).
- **Review & Auditability**: `created_by_user_id`, `reviewed_by_user_id`, `reviewed_at`, `progress_notes`.

### 4.2 Actionable Care Tasks & Follow-Up Management (`CareTask`)
- **Task Types**: `followup_appointment`, `lab_test_order`, `diagnostic_imaging_order`, `patient_education`, `medication_reconciliation`, `telemetry_check`, `general_task`.
- **Priority**: `LOW`, `ROUTINE`, `URGENT`, `STAT`.
- **Status Lifecycle**: `pending` -> `in_progress` -> `completed` / `cancelled`.
- **Due Dates & Overdue Flagging**: Automatic calculation of overdue status when `due_date < now() && status != 'completed'`.
- **Assignment**: Assigned to specific clinician (`assigned_doctor_id`) or staff user (`assigned_user_id`).

### 4.3 AI-Assisted Care Plan Generation (`BaseCarePlanProvider` / `MockCarePlanProvider`)
- Synthesizes patient clinical profile across active conditions, recent SOAP notes, imaging findings, and vital anomalies.
- Generates assistive draft care plans with suggested goals and interventions.
- Strictly non-autonomous: Every AI-generated plan remains in `draft` state until explicit physician review and activation.

---

## 5. Explicit Non-Goals
- No autonomous ordering of pharmaceuticals or invasive procedures.
- No direct dispatching of real external clinical orders without physician confirmation.
- No dependency on paid external AI APIs (Mock provider remains default for testing and offline development).
- No mutation of closed/completed care plans without explicit amendment audit logging.

---

## 6. Proposed Database Schema (Migration `0012_care_plans_and_tasks`)

### 6.1 Table: `care_plans`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Autoincrement | Internal ID |
| `plan_id` | String(32) | Unique Index, Not Null | Public ID (`CP-YYYYMMDD-XXXXXX`) |
| `patient_id` | Integer | FK -> `patients.id` (RESTRICT), Index | Target patient |
| `author_user_id` | Integer | FK -> `users.id` (SET NULL), Nullable | Clinician author |
| `encounter_id` | Integer | FK -> `encounters.id` (SET NULL), Nullable | Associated encounter |
| `title` | String(255) | Not Null | Care plan title |
| `category` | String(50) | Default: 'chronic_disease_management' | Care plan domain |
| `status` | String(30) | Default: 'draft', Index | `draft`, `reviewed`, `active`, `completed`, `cancelled` |
| `intent` | String(30) | Default: 'plan' | FHIR intent (`proposal`, `plan`, `order`) |
| `description` | Text | Not Null | Clinical overview & objectives |
| `goals_json` | JSON | Nullable | Structured health goals |
| `interventions_json` | JSON | Nullable | Structured interventions & activities |
| `is_ai_generated` | Boolean | Default: False | Flag indicating AI drafting |
| `reviewed_by_user_id` | Integer | FK -> `users.id` (SET NULL), Nullable | Reviewing physician |
| `reviewed_at` | DateTime(tz) | Nullable | Timestamp of clinician signoff |
| `start_date` | DateTime(tz) | Not Null | Effective start timestamp |
| `end_date` | DateTime(tz) | Nullable | Target completion timestamp |
| `created_at` | DateTime(tz) | Default: now(), Not Null | Creation timestamp |
| `updated_at` | DateTime(tz) | Default: now(), Not Null | Last modification timestamp |

### 6.2 Table: `care_tasks`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Autoincrement | Internal ID |
| `task_id` | String(32) | Unique Index, Not Null | Public ID (`CTSK-YYYYMMDD-XXXXXX`) |
| `patient_id` | Integer | FK -> `patients.id` (RESTRICT), Index | Associated patient |
| `care_plan_id` | Integer | FK -> `care_plans.id` (CASCADE), Nullable | Associated care plan |
| `encounter_id` | Integer | FK -> `encounters.id` (SET NULL), Nullable | Associated encounter |
| `appointment_id` | Integer | FK -> `appointments.id` (SET NULL), Nullable | Associated appointment |
| `assigned_user_id` | Integer | FK -> `users.id` (SET NULL), Nullable | Assigned staff/clinician |
| `title` | String(255) | Not Null | Task description |
| `task_type` | String(50) | Default: 'general_task' | Task classification |
| `priority` | String(20) | Default: 'ROUTINE', Index | `LOW`, `ROUTINE`, `URGENT`, `STAT` |
| `status` | String(20) | Default: 'pending', Index | `pending`, `in_progress`, `completed`, `cancelled` |
| `instructions` | Text | Nullable | Detailed instructions for the task |
| `due_date` | DateTime(tz) | Not Null, Index | Task deadline |
| `completed_at` | DateTime(tz) | Nullable | Completion timestamp |
| `completion_notes` | Text | Nullable | Clinician/staff outcome notes |
| `created_at` | DateTime(tz) | Default: now(), Not Null | Creation timestamp |

---

## 7. Migration Number & Lineage
- **Revision ID**: `0012_care_plans_and_tasks`
- **Revises**: `0011_vitals_and_clinical_alerts`
- **Chain**: `0001` -> `0010` -> `0011` -> `0012`

---

## 8. Backend Models & ORM Entities
- `CarePlan` in `backend/app/models/care_plan.py`
- `CareTask` in `backend/app/models/care_task.py`
- Expose in `backend/app/models/__init__.py`.

---

## 9. Pydantic Schemas
- `backend/app/schemas/care_plan.py`:
  - `CarePlanStatus`, `CarePlanCategory`, `CarePlanGoal`, `CarePlanIntervention`, `CarePlanCreate`, `CarePlanUpdate`, `CarePlanReviewRequest`, `CarePlanResponse`, `CarePlanListResponse`, `CarePlanSynthesizeRequest`.
- `backend/app/schemas/care_task.py`:
  - `TaskPriority`, `CareTaskStatus`, `CareTaskType`, `CareTaskCreate`, `CareTaskUpdate`, `CareTaskCompleteRequest`, `CareTaskResponse`, `CareTaskListResponse`.
- Expose in `backend/app/schemas/__init__.py`.

---

## 10. Service Layer & Business Logic
- `backend/app/services/care_plan_service.py`:
  - Care plan CRUD, goal/intervention tracking, physician signoff & review.
  - Task assignment, status transitions, overdue computation.
  - Context aggregation for AI synthesis.
- `backend/app/ai/care_plan_provider.py`:
  - `BaseCarePlanProvider` (abstract base class).
  - `MockCarePlanProvider` (deterministic, zero-cloud offline provider).

---

## 11. API Endpoints

| Method | Endpoint | Access Role | Description |
|---|---|---|---|
| `POST` | `/api/v1/patients/{patient_id}/care-plans` | Doctor, Staff, Admin | Create a new structured care plan |
| `GET` | `/api/v1/patients/{patient_id}/care-plans` | Authenticated / Isolated | List care plans for a patient |
| `GET` | `/api/v1/care-plans/{plan_id}` | Authenticated / Isolated | Retrieve specific care plan details |
| `PATCH` | `/api/v1/care-plans/{plan_id}` | Doctor, Staff, Admin | Update draft care plan |
| `POST` | `/api/v1/care-plans/{plan_id}/review` | Doctor, Admin | Attending physician review and activation |
| `POST` | `/api/v1/tasks/care-plans/synthesize` | Doctor, Staff, Admin | Trigger background AI care plan drafting |
| `POST` | `/api/v1/patients/{patient_id}/care-tasks` | Doctor, Staff, Admin | Create a clinical follow-up task |
| `GET` | `/api/v1/patients/{patient_id}/care-tasks` | Authenticated / Isolated | List follow-up tasks for a patient |
| `PATCH` | `/api/v1/care-tasks/{task_id}` | Doctor, Staff, Admin | Update task status, priority, or assignee |
| `POST` | `/api/v1/care-tasks/{task_id}/complete` | Doctor, Staff, Admin | Mark task complete with outcome notes |

---

## 12. Background Task Worker Integration
- Add `BackgroundTaskType.CARE_PLAN_GENERATION = "care_plan_generation"`.
- Implement async job `process_care_plan_synthesis_task` in `backend/app/services/care_plan_service.py`.

---

## 13. AI Provider Abstraction
- Defined in `backend/app/ai/care_plan_provider.py`.
- Deterministic response synthesis for testing (evaluates chronic hypertension, diabetes, hypoxia, tachycardia profiles).

---

## 14. FHIR R4 Interoperability Strategy
- Add `export_care_plan_to_fhir(care_plan: CarePlan) -> dict` in `backend/app/services/fhir_service.py`.
- Maps to FHIR R4 `CarePlan` resource with `goal` and `activity` structures.
- Add `export_care_task_to_fhir(task: CareTask) -> dict` mapping to FHIR R4 `Task`.

---

## 15. Frontend Care Coordination Workspace
- Create `frontend/src/components/care/CarePlanWorkspace.tsx`:
  - Active care plan overview card (Title, Status, Intent, Start/End dates).
  - Health Goals checklist with status badges.
  - Interventions list.
  - Follow-up Task Kanban / List with Priority (`STAT`, `URGENT`, `ROUTINE`) and overdue alerts.
  - "⚡ Generate AI Care Plan" action.
  - Physician review/activation button.
  - Add task modal/inline form.
- Add `📋 Care Plans & Tasks` tab in `frontend/src/pages/DashboardPage.tsx`.

---

## 16. Security, RBAC & Patient Isolation
- `PATIENT` role: Read-only access to their own care plans and tasks.
- `HEALTHCARE_STAFF` role: Can create care plans, create tasks, update task status, and mark tasks complete.
- `DOCTOR` & `ADMIN` roles: Full control including care plan review, signoff, and activation.
- Cross-patient access strictly prohibited (`403 Forbidden`).
- Zero PHI in operational logs.

---

## 17. Auditability & Immutability Rules
- Once a care plan is marked `completed` or `cancelled`, it cannot be modified directly (requires an explicit amendment).
- Physician reviews record `reviewed_by_user_id` and `reviewed_at`.
- Task completions record `completed_at` and `completion_notes`.

---

## 18. Testing Strategy
- Create `backend/tests/test_care_plans_and_tasks.py`:
  - Care plan creation and validation.
  - Goal and intervention JSON structure.
  - Physician review and lifecycle transition (`draft` -> `active`).
  - Task creation, priority, and overdue detection.
  - Task completion with outcome notes.
  - Background AI Care Plan synthesis worker job.
  - FHIR R4 export formatting.
  - RBAC and patient isolation.
- Create `frontend/src/test/care.test.tsx`:
  - Workspace rendering.
  - Goal and intervention display.
  - Task completion flow.
  - AI synthesis trigger.

---

## 19. Regression Strategy
- Validate all existing 334 backend tests and 16 frontend unit tests continue to pass with 0 regressions.
- Verify complete frontend production build.

---

## 20. Exact Files Expected to Be Created / Modified

### New Files (11):
1. `backend/alembic/versions/0012_care_plans_and_tasks.py`
2. `backend/app/models/care_plan.py`
3. `backend/app/models/care_task.py`
4. `backend/app/schemas/care_plan.py`
5. `backend/app/schemas/care_task.py`
6. `backend/app/ai/care_plan_provider.py`
7. `backend/app/services/care_plan_service.py`
8. `backend/app/api/v1/endpoints/care_plans.py`
9. `backend/tests/test_care_plans_and_tasks.py`
10. `docs/phase_9_0_10.md`
11. `frontend/src/components/care/CarePlanWorkspace.tsx`
12. `frontend/src/test/care.test.tsx`

### Modified Files (8):
1. `backend/app/models/__init__.py`
2. `backend/app/schemas/__init__.py`
3. `backend/app/schemas/task.py`
4. `backend/app/services/fhir_service.py`
5. `backend/app/api/v1/api.py`
6. `frontend/src/types/index.ts`
7. `frontend/src/api/client.ts`
8. `frontend/src/pages/DashboardPage.tsx`
9. `README.md`

---

## 21. Rollback & Backward Compatibility Considerations
- Migration `0012` downgrade cleanly drops `care_tasks` and `care_plans` tables.
- Zero breaking modifications to existing patient, appointment, encounter, or note schemas.

---

## 22. Implementation Order
1. Backend schemas (`care_plan.py`, `care_task.py`).
2. Database models (`care_plan.py`, `care_task.py`) & export in `__init__.py`.
3. Alembic migration `0012_care_plans_and_tasks.py`.
4. AI Provider `care_plan_provider.py` & Task Worker integration.
5. Service layer `care_plan_service.py` & FHIR extension.
6. API Endpoints `care_plans.py` & registration in `api.py`.
7. Frontend types, API client methods, `CarePlanWorkspace.tsx`, and tab in `DashboardPage.tsx`.
8. Comprehensive backend tests & frontend tests.
9. Documentation & verification.

---

## 23. Acceptance Criteria
- All care plan and task CRUD endpoints return proper responses with RBAC enforcement.
- AI care plan synthesis executes synchronously or asynchronously via background task worker.
- Physician signoff transitions plans from `draft` to `active`.
- Frontend care workspace renders goals, interventions, tasks, and overdue badges.
- 100% test pass rate on backend and frontend suites.
