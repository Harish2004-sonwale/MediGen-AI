# Phase 9.0.12 Implementation Plan: Clinical Transitions of Care, Multi-Disciplinary Handoffs (IPASS/SBAR) & Automated Discharge Protocol Synthesis

## 1. Executive Summary & Clinical Context
In acute and ambulatory clinical environments, transitions of care—such as physician shift handoffs, inter-departmental transfers, and patient hospital discharges—represent the highest-risk windows for medical errors, missed follow-ups, and preventable 30-day readmissions.

Phase 9.0.12 introduces **Transitions of Care & Multi-Disciplinary Clinical Handoff Orchestration** into MediGen-AI:
1. **Standardized Clinical Handoffs**: Implementing evidence-based **I-PASS** (*Illness Severity, Patient Summary, Action List, Situation Awareness & Contingencies, Synthesis by Receiver*) and **SBAR** (*Situation, Background, Assessment, Recommendation*) shift-handoff and transfer protocols.
2. **Discharge Planning & Protocol Synthesis**: Structured continuity-of-care discharge packages including automated hospital course synthesis, discharge medication reconciliation, pending test tracking, follow-up appointment coordination, and patient-centric red-flag warning instructions.
3. **Multi-Disciplinary Signoff Workflow**: Clinician-in-the-loop validation requiring attending physician signoff, nursing review, and pharmacist medication reconciliation.
4. **FHIR R4 Interoperability**: Standardized mapping to FHIR R4 `Composition` (Discharge Summaries / Continuity of Care Documents) and FHIR R4 `Communication` (Handoff Messages).
5. **Assistive Offline AI Synthesis**: Deterministic, offline-first synthesis aggregating clinical data across past encounters, notes, vitals, CDS alerts, care plans, and risk assessments into structured handoff and discharge packages.

---

## 2. Database Architecture & Alembic Migration 0014

### A. New Models in `backend/app/models/`
1. `backend/app/models/handoff.py`:
   - **`ClinicalHandoff`** (`clinical_handoffs` table):
     - `id`: Integer primary key
     - `handoff_id`: String(32) unique index (e.g., `HDF-20260829-XXXXXXXX`)
     - `patient_id`: Integer foreign key -> `patients.id` (ON DELETE RESTRICT, index)
     - `encounter_id`: Integer foreign key -> `encounters.id` (ON DELETE SET NULL, index)
     - `sender_user_id`: Integer foreign key -> `users.id` (ON DELETE SET NULL)
     - `receiver_user_id`: Integer foreign key -> `users.id` (ON DELETE SET NULL)
     - `framework`: String(20) (`ipass` or `sbar`)
     - `handoff_type`: String(30) (`shift_change`, `unit_transfer`, `discharge_transition`, `service_consultation`)
     - `illness_severity`: String(20) (`stable`, `watcher`, `unstable`)
     - `status`: String(20) (`draft`, `active`, `acknowledged`, `completed`, `cancelled`)
     - `summary`: Text (Patient background / clinical summary)
     - `action_items_json`: JSON (Structured list of pending actions with responsible roles and deadlines)
     - `situational_awareness_json`: JSON (Contingency plans: "If X happens, do Y")
     - `synthesis_notes`: Text (Receiver read-back / acknowledgment notes)
     - `is_ai_generated`: Boolean (default True)
     - `acknowledged_at`: Timestamp with time zone
     - `created_at` / `updated_at`: Timestamps with time zone

2. `backend/app/models/discharge.py`:
   - **`DischargeProtocol`** (`discharge_protocols` table):
     - `id`: Integer primary key
     - `discharge_id`: String(32) unique index (e.g., `DIS-20260829-XXXXXXXX`)
     - `patient_id`: Integer foreign key -> `patients.id` (ON DELETE RESTRICT, index)
     - `encounter_id`: Integer foreign key -> `encounters.id` (ON DELETE SET NULL, index)
     - `attending_user_id`: Integer foreign key -> `users.id` (ON DELETE SET NULL)
     - `nurse_user_id`: Integer foreign key -> `users.id` (ON DELETE SET NULL)
     - `pharmacist_user_id`: Integer foreign key -> `users.id` (ON DELETE SET NULL)
     - `status`: String(20) (`draft`, `under_review`, `ready_for_discharge`, `completed`, `cancelled`)
     - `disposition`: String(40) (`home_self_care`, `home_health_services`, `skilled_nursing_facility`, `rehab_facility`, `hospice`, `transfer_acute_care`)
     - `discharge_date`: Timestamp with time zone
     - `hospital_course_summary`: Text
     - `primary_discharge_diagnosis`: String(255)
     - `secondary_diagnoses_json`: JSON (List of resolved / ongoing secondary conditions)
     - `medication_reconciliation_json`: JSON (List of reconciled medications with status: `continued`, `dosage_adjusted`, `discontinued`, `newly_prescribed`)
     - `followup_instructions_json`: JSON (Follow-up appointments, provider names, timeframes)
     - `pending_tests_json`: JSON (Diagnostic tests / lab cultures pending at time of discharge)
     - `warning_symptoms_json`: JSON (Red-flag symptoms requiring emergency department presentation)
     - `activity_and_diet_instructions`: Text
     - `is_ai_generated`: Boolean (default True)
     - `signed_off_at`: Timestamp with time zone
     - `created_at` / `updated_at`: Timestamps with time zone

### B. Alembic Migration:
- `backend/alembic/versions/0014_transitions_and_discharge_protocols.py`:
  - Upgrades from `0013_cohorts_and_risk_stratification` to `0014_transitions_and_discharge_protocols`.
  - Creates `clinical_handoffs` and `discharge_protocols` tables, foreign keys, and indexes.

---

## 3. Pydantic Schemas

### A. `backend/app/schemas/handoff.py`:
- `HandoffFramework` enum (`ipass`, `sbar`)
- `HandoffType` enum (`shift_change`, `unit_transfer`, `discharge_transition`, `service_consultation`)
- `IllnessSeverity` enum (`stable`, `watcher`, `unstable`)
- `HandoffStatus` enum (`draft`, `active`, `acknowledged`, `completed`, `cancelled`)
- `HandoffActionItem` schema (item_id, task_description, role_required, priority, is_completed)
- `ContingencyPlan` schema (trigger_condition, immediate_action, escalation_contact)
- `HandoffCreate`, `HandoffUpdate`, `HandoffAcknowledge`, `HandoffResponse`, `HandoffListResponse`

### B. `backend/app/schemas/discharge.py`:
- `DischargeDisposition` enum (`home_self_care`, `home_health_services`, `skilled_nursing_facility`, `rehab_facility`, `hospice`, `transfer_acute_care`)
- `DischargeStatus` enum (`draft`, `under_review`, `ready_for_discharge`, `completed`, `cancelled`)
- `ReconciledMedication` schema (medication_name, dose, route, frequency, status, clinical_rationale)
- `FollowupAppointment` schema (provider_or_specialty, timeframe, contact_info, purpose)
- `PendingDiagnosticTest` schema (test_name, ordered_date, follow_up_physician, expected_result_timeline)
- `DischargeProtocolCreate`, `DischargeProtocolUpdate`, `DischargeSignoffRequest`, `DischargeProtocolResponse`, `DischargeProtocolListResponse`

---

## 4. Deterministic AI Provider & Service Architecture

### A. AI Provider in `backend/app/ai/handoff_provider.py`
- `BaseHandoffDischargeProvider` abstract interface.
- `MockHandoffDischargeProvider` deterministic offline implementation:
  - Ingests patient age, diagnoses, active encounters, recent vitals & CDS alerts, care plans, and risk assessments.
  - Synthesizes:
    - **I-PASS Handoff**: Classifies illness severity based on recent vital alerts/risk scores; generates concise patient summary, prioritized action list, and vital contingency rules.
    - **SBAR Handoff**: Synthesizes Situation, Background, Assessment, and Recommendation.
    - **Discharge Protocol**: Auto-generates hospital course narrative, identifies ongoing vs. resolved diagnoses, performs baseline medication reconciliation, compiles follow-up instructions, and generates disease-specific red-flag warnings.

### B. Service Layer in `backend/app/services/handoff_service.py`
- Handoff CRUD, receiver acknowledgment, and shift assignment.
- Discharge protocol CRUD, multi-disciplinary review, attending physician signoff, and completion.
- Background worker execution functions:
  - `execute_handoff_synthesis_job(patient_id, framework, handoff_type)`
  - `execute_discharge_synthesis_job(patient_id, encounter_id, disposition)`

---

## 5. FHIR R4 Interoperability

### A. Resource Types & Mappings in `fhir.py` & `fhir_mapper_service.py`
- Adds `COMPOSITION` and `COMMUNICATION` to `FHIRResourceType`.
- **`FHIRComposition`**: Maps `DischargeProtocol` to standardized FHIR R4 `Composition` (Type: `18842-5` Discharge Summary, Status: `final` / `preliminary`, Sections for Hospital Course, Discharge Medications, Follow-Up, and Warning Signs).
- **`FHIRCommunication`**: Maps `ClinicalHandoff` to standardized FHIR R4 `Communication` (Category: `clinical-handoff`, Sender reference, Recipient reference, Payload content).
- Export endpoints in `fhir.py`:
  - `GET /api/v1/fhir/Composition/{discharge_id}`
  - `GET /api/v1/fhir/Communication/{handoff_id}`

---

## 6. REST API Endpoints

| Method | Endpoint | Access | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/patients/{patient_id}/handoffs` | Clinical Roles | Create or synthesize structured shift handoff (I-PASS / SBAR) |
| `GET` | `/api/v1/patients/{patient_id}/handoffs` | Authenticated | List historical handoffs for patient |
| `GET` | `/api/v1/handoffs/{handoff_id}` | Authenticated | Retrieve specific handoff details |
| `PATCH` | `/api/v1/handoffs/{handoff_id}` | Clinical Roles | Update handoff items and contingency plans |
| `POST` | `/api/v1/handoffs/{handoff_id}/acknowledge` | Clinical Roles | Receiving clinician formal synthesis and signoff |
| `POST` | `/api/v1/patients/{patient_id}/discharge-protocols` | Clinical Roles | Create or synthesize discharge protocol package |
| `GET` | `/api/v1/patients/{patient_id}/discharge-protocols` | Authenticated | List discharge protocols for patient |
| `GET` | `/api/v1/discharge-protocols/{discharge_id}` | Authenticated | Retrieve discharge protocol details |
| `PATCH` | `/api/v1/discharge-protocols/{discharge_id}` | Clinical Roles | Update discharge instructions and medication reconciliation |
| `POST` | `/api/v1/discharge-protocols/{discharge_id}/signoff` | Doctor / Admin | Attending physician review and legal signoff |
| `POST` | `/api/v1/tasks/patients/{patient_id}/handoff/synthesize` | Clinical Roles | Enqueue background AI handoff synthesis |
| `POST` | `/api/v1/tasks/patients/{patient_id}/discharge/synthesize` | Clinical Roles | Enqueue background AI discharge protocol synthesis |
| `GET` | `/api/v1/fhir/Composition/{discharge_id}` | Authenticated | Export discharge protocol as FHIR R4 Composition |
| `GET` | `/api/v1/fhir/Communication/{handoff_id}` | Authenticated | Export handoff as FHIR R4 Communication |

---

## 7. Frontend Transitions & Discharge Workspace

- **`TransitionsWorkspace.tsx`** in `frontend/src/components/transitions/`:
  - **Handoff Hub**:
    - Framework switcher: **I-PASS** (Illness Severity, Summary, Actions, Contingencies) vs. **SBAR** (Situation, Background, Assessment, Recommendation).
    - Status badges (`Stable` [green], `Watcher` [yellow], `Unstable` [red]).
    - Interactive action items checklist & contingency instructions.
    - "🤝 Acknowledge Handoff" clinician signoff dialog.
  - **Discharge Protocol Hub**:
    - Comprehensive discharge package builder.
    - Reconciled medications grid with change rationale badges (`Continued`, `Adjusted`, `Stopped`, `New`).
    - Follow-up appointment schedule & pending lab tracking.
    - Patient emergency red-flag warning criteria.
    - "✍️ Attending Signoff & Finalize Discharge" approval flow.
- **Integration**:
  - Add tab `🔄 Transitions & Discharge` to `frontend/src/pages/DashboardPage.tsx`.
  - Add `transitionsApi` to `frontend/src/api/client.ts`.
  - Add TypeScript interfaces to `frontend/src/types/index.ts`.

---

## 8. Security & Clinical Safety Principles
1. **Clinician-in-the-Loop**: Generated handoffs and discharge summaries are explicitly marked as assistive drafts (`status='draft'`) requiring manual clinical review, reconciliation, and attending physician signoff before finalization.
2. **Zero PHI Exposure in Logs**: Structured audit logging records entity IDs and action outcomes; zero raw patient identifiers or medical narratives in operational logs.
3. **Strict RBAC & Patient Isolation**:
   - Patient users can view only their own finalized discharge protocols and handoffs.
   - Shift handoffs and discharge protocol generation/editing are restricted to `DOCTOR`, `HEALTHCARE_STAFF`, and `ADMIN`.
4. **Offline Deterministic Fallbacks**: Risk-informed handoff generation operates with zero external network dependencies.

---

## 9. Exact Files to Create and Modify

### Files to Create:
1. `backend/app/models/handoff.py`
2. `backend/app/models/discharge.py`
3. `backend/app/schemas/handoff.py`
4. `backend/app/schemas/discharge.py`
5. `backend/alembic/versions/0014_transitions_and_discharge_protocols.py`
6. `backend/app/ai/handoff_provider.py`
7. `backend/app/services/handoff_service.py`
8. `backend/app/api/v1/endpoints/transitions.py`
9. `backend/tests/test_transitions_and_discharge.py`
10. `frontend/src/components/transitions/TransitionsWorkspace.tsx`
11. `frontend/src/test/transitions.test.tsx`
12. `docs/phase_9_0_12.md`

### Files to Modify:
1. `backend/app/models/__init__.py`: Export `ClinicalHandoff`, `DischargeProtocol`.
2. `backend/app/schemas/__init__.py`: Export transition and discharge schemas.
3. `backend/app/schemas/task.py`: Add `HANDOFF_SYNTHESIS`, `DISCHARGE_SYNTHESIS` task types.
4. `backend/app/schemas/fhir.py`: Add `COMPOSITION`, `COMMUNICATION` enum values and schemas.
5. `backend/app/services/fhir_mapper_service.py`: Add `FHIRCompositionMapper` and `FHIRCommunicationMapper`.
6. `backend/app/services/fhir_export_service.py`: Add export functions for Composition and Communication.
7. `backend/app/api/v1/endpoints/fhir.py`: Add `Composition` and `Communication` endpoints.
8. `backend/app/api/v1/api.py`: Register `transitions.router`.
9. `frontend/src/types/index.ts`: Add transition and discharge TypeScript types.
10. `frontend/src/api/client.ts`: Add `transitionsApi`.
11. `frontend/src/pages/DashboardPage.tsx`: Add `🔄 Transitions & Discharge` tab.
12. `README.md`: Update API documentation and roadmap.

---

## 10. Verification Strategy
1. **Focused Backend Tests**: `pytest backend/tests/test_transitions_and_discharge.py` (target: 7+ tests covering CRUD, IPASS/SBAR generation, medication reconciliation, attending signoff, FHIR exports, RBAC).
2. **Full Regression Test**: `pytest backend/tests -q` (target: 355+ passed, 2 skipped across 42 test files).
3. **Frontend Unit Tests**: `npm test -- --run` (target: 25+ passed across 10 test suites).
4. **Frontend Production Build**: `npm run build` (`tsc && vite build`).
5. **Alembic SQL Validation**: `alembic upgrade head --sql` verifying migration 0014.
6. **Git Quality & Secrets**: `git diff --cached --check` and secret audit.
