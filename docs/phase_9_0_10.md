# Phase 9.0.10 — Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management

## 1. Overview
Phase 9.0.10 introduces longitudinal clinical workflow orchestration into MediGen-AI, providing structured clinical care plans, health goals tracking, actionable follow-up task pipelines, and FHIR R4 interoperability for care coordination.

## 2. Key Architecture Components

### A. Clinical Care Plans & Goals
- **Model**: `CarePlan` (`care_plans` table) with structured JSON columns for `goals_json` and `interventions_json`.
- **Domain Categories**:
  - `chronic_disease_management`: Hypertension, diabetes, COPD longitudinal regimens.
  - `post_discharge_followup`: Transitional post-inpatient monitoring.
  - `preventive_care`: Wellness, screening, and lifestyle management.
  - `rehabilitation`: Physical therapy, cardiac rehab, post-surgical recovery.
  - `acute_care_plan`: Episode-specific management.
- **Lifecycle & Safety**:
  - States: `draft` -> `reviewed` -> `active` -> `completed` / `suspended` / `cancelled`.
  - All AI-generated care plans start in `DRAFT` status and cannot become `active` without explicit physician verification (`confirm_accuracy=True`).
  - Completed and cancelled plans are legally immutable.

### B. Actionable Clinical Tasks & Overdue Detection
- **Model**: `CareTask` (`care_tasks` table) linked to `CarePlan`, `Patient`, `Encounter`, and `Appointment`.
- **Task Types**: `followup_appointment`, `lab_test_order`, `diagnostic_imaging_order`, `patient_education`, `medication_reconciliation`, `telemetry_check`, `general_task`.
- **Priorities**: `LOW`, `ROUTINE`, `URGENT`, `STAT`.
- **Dynamic Overdue Computation**: `is_overdue = (task.due_date < now && task.status != completed)`.
- **Task Outcomes**: Complete endpoint records `completed_at` timestamp and clinician `completion_notes`.

### C. Deterministic Offline AI Care Plan Provider
- `BaseCarePlanProvider` and `MockCarePlanProvider` synthesize patient longitudinal history, active conditions, medications, recent vitals, CDS alerts, and custom clinician focus directives into structured care plan drafts and recommended follow-up tasks.
- Zero GPU requirements, zero external API keys, 100% deterministic offline execution.

### D. FHIR R4 Interoperability
- Bidirectional mapper and serializer:
  - `FHIRCarePlanMapper.to_fhir(care_plan)` -> FHIR R4 `CarePlan` with embedded `activity` and linked `Goal` references.
  - `FHIRTaskMapper.to_fhir(care_task)` -> FHIR R4 `Task`.
- Endpoints:
  - `GET /api/v1/fhir/CarePlan/{care_plan_id}`
  - `GET /api/v1/fhir/Task/{task_id}`

### E. Frontend Care Coordination Workspace
- **Component**: `CarePlanWorkspace.tsx` in `frontend/src/components/care/` integrated into `DashboardPage.tsx` under `📋 Care Plans & Tasks`.
- Features:
  - Care Plan selector & active plan card.
  - Health Goals checklist with target metrics.
  - Planned interventions with responsible roles.
  - Clinical Follow-Up Tasks table with priority and overdue badges.
  - Inline task completion modal with outcome notes.
  - AI Care Plan synthesis modal with domain category selection.
  - Attending physician review and activation signoff modal.

## 3. Database Migration
- **Migration**: `0012_care_plans_and_tasks.py`
- Chain: `0001` -> `...` -> `0011_vitals_and_clinical_alerts` -> `0012_care_plans_and_tasks`.
- Creates `care_plans` and `care_tasks` tables with proper foreign keys (`CASCADE` on care plan deletion, `RESTRICT` on patient deletion), indexes on identifiers, foreign keys, priorities, and statuses.

## 4. Verification Results
- **Backend Test Suite**: 341 passed, 2 skipped (100% passing across 40 test files).
- **Frontend Test Suite**: 19 passed across 8 test suites.
- **Frontend Production Build**: Clean Vite + TypeScript build (`247 kB` gzip: `66 kB`).
- **Alembic Migration**: `upgrade head --sql` validated for PostgreSQL.
- **Security / Git Cleanliness**: `git diff --check` passed with zero errors.
