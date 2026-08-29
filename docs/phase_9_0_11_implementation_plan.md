# Phase 9.0.11 Implementation Plan — Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification

## 1. Executive Summary & Clinical Purpose
Phase 9.0.11 establishes Population Health Intelligence and Clinical Risk Stratification within MediGen-AI. It empowers clinical directors, attending physicians, and care managers to manage dynamic patient disease registries (e.g. Hypertension, Uncontrolled Diabetes, Post-Inpatient Readmission Watch, Sepsis Vulnerability), calculate multi-factorial longitudinal clinical risk scores, and track aggregate population health metrics.

---

## 2. Existing Components Reused
1. **Core Database Entities**:
   - `Patient`, `Encounter`, `VitalTelemetry`, `ClinicalAlert`, `CarePlan`, `CareTask` models as feature sources for clinical risk scoring.
2. **Background Task Worker Architecture**:
   - `LocalBackgroundTaskProvider`, `SyncBackgroundTaskProvider`, and `CeleryBackgroundTaskProvider` via `submit_task`.
3. **FHIR R4 Foundation**:
   - Base mapping structures and serializers in `backend/app/services/fhir_mapper_service.py` and `fhir_export_service.py`.
4. **Security & RBAC**:
   - `require_role`, `get_current_active_user`, and strict patient isolation protocols.
5. **Frontend Design System**:
   - Glassmorphism UI tokens, CSS variables, `api/client.ts`, and component patterns.

---

## 3. Database Layer Architecture

### A. New SQLAlchemy Models
File: `backend/app/models/cohort.py`
- **`PatientCohort`** (`patient_cohorts` table):
  - `id`: Integer, primary_key=True
  - `cohort_id`: String(32), unique=True, index=True (e.g. `COHORT-20260829-XXXXXXXX`)
  - `name`: String(255), nullable=False, index=True
  - `description`: Text, nullable=False
  - `cohort_type`: String(50), default="disease_registry", nullable=False, index=True
  - `criteria_json`: JSON, nullable=True (rules for age, conditions, vital bounds, risk tier)
  - `is_dynamic`: Boolean, default=True, nullable=False
  - `created_by_user_id`: Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
  - `created_at`: DateTime(timezone=True), default=utc_now
  - `updated_at`: DateTime(timezone=True), default=utc_now

- **`CohortMembership`** (`cohort_memberships` table):
  - `id`: Integer, primary_key=True
  - `cohort_id`: Integer, ForeignKey("patient_cohorts.id", ondelete="CASCADE"), nullable=False, index=True
  - `patient_id`: Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
  - `enrolled_at`: DateTime(timezone=True), default=utc_now
  - `status`: String(30), default="active", nullable=False
  - `notes`: Text, nullable=True
  - UniqueConstraint: `("cohort_id", "patient_id")`

File: `backend/app/models/risk_assessment.py`
- **`ClinicalRiskAssessment`** (`clinical_risk_assessments` table):
  - `id`: Integer, primary_key=True
  - `assessment_id`: String(32), unique=True, index=True (e.g. `RISK-20260829-XXXXXXXX`)
  - `patient_id`: Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True
  - `encounter_id`: Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True
  - `risk_type`: String(50), nullable=False, index=True
  - `risk_score`: Float, nullable=False (0.0 to 100.0)
  - `risk_tier`: String(20), default="MODERATE", nullable=False, index=True
  - `predicted_outcome`: String(255), nullable=False
  - `contributing_factors_json`: JSON, nullable=True (list of {factor, severity, value, rationale})
  - `mitigation_recommendations_json`: JSON, nullable=True (suggested clinical interventions)
  - `assessed_by_user_id`: Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
  - `is_ai_generated`: Boolean, default=True, nullable=False
  - `assessed_at`: DateTime(timezone=True), default=utc_now, index=True
  - `created_at`: DateTime(timezone=True), default=utc_now

### B. Database Migration
File: `backend/alembic/versions/0013_cohorts_and_risk_stratification.py`
- Down revision: `0012_care_plans_and_tasks`
- Creates `patient_cohorts`, `cohort_memberships`, `clinical_risk_assessments` tables, foreign keys, and indexes.

---

## 4. Domain Schemas & Enums

### A. Cohort Schemas (`backend/app/schemas/cohort.py`)
- `CohortType`: `disease_registry`, `risk_watch_list`, `post_op_monitoring`, `quality_measure`, `custom_cohort`
- `CohortCriteria`: age range, conditions, medication filters, vitals ranges, minimum risk score
- `CohortCreate`, `CohortUpdate`, `CohortResponse`, `CohortListResponse`
- `CohortMembershipCreate`, `CohortMembershipResponse`
- `CohortAnalyticsResponse`: total patients, risk tier breakdown, mean score, alert volume, care plan coverage

### B. Risk Assessment Schemas (`backend/app/schemas/risk_assessment.py`)
- `RiskType`: `readmission_30d`, `cardiovascular_decompensation`, `clinical_deterioration`, `medication_adherence`, `general_mortality`
- `RiskTier`: `LOW`, `MODERATE`, `HIGH`, `CRITICAL`
- `RiskFactor`: factor name, category, weight/severity, observation value, explanation
- `RiskMitigationAction`: recommended action, priority, suggested task type
- `RiskAssessmentCreate`, `RiskAssessmentResponse`, `RiskAssessmentListResponse`, `RiskStratifyRequest`

---

## 5. Risk Stratification Engine & Provider Architecture

### A. Provider Interface (`backend/app/ai/risk_provider.py`)
- `BaseRiskStratificationProvider` (ABC):
  - `calculate_risk(patient_data: dict, risk_type: RiskType) -> dict`
- `MockRiskStratificationProvider`:
  - Deterministic clinical heuristic algorithm:
    - Analyzes patient age (>65 adds risk).
    - Checks medical history (hypertension, diabetes, heart failure, COPD).
    - Evaluates vital telemetry (tachycardia HR > 100, hypertension SBP > 140, hypoxemia SpO2 < 92%).
    - Evaluates active CDS alerts and recurrence counts.
    - Evaluates overdue follow-up tasks and care plan adherence.
    - Outputs quantitative score (0-100), risk tier, list of contributing factors, and mitigation steps.
  - 100% offline, zero GPU requirement, zero external API keys.

---

## 6. Service Layer Architecture

### File: `backend/app/services/cohort_service.py`
1. **Cohort CRUD**:
   - `create_cohort(db, cohort_in, current_user)`
   - `list_cohorts(db, current_user, cohort_type)`
   - `get_cohort(db, cohort_id, current_user)`
   - `update_cohort(db, cohort_id, cohort_in, current_user)`
   - `delete_cohort(db, cohort_id, current_user)`
2. **Membership & Dynamic Evaluation**:
   - `add_cohort_member(db, cohort_id, patient_id, notes, current_user)`
   - `remove_cohort_member(db, cohort_id, patient_id, current_user)`
   - `evaluate_dynamic_cohort_membership(db, cohort_id)`
3. **Risk Stratification**:
   - `assess_patient_risk(db, patient_id, risk_type, current_user)`
   - `list_patient_risk_assessments(db, patient_id, current_user, risk_type)`
   - `get_risk_assessment(db, assessment_id, current_user)`
4. **Cohort Population Analytics**:
   - `get_cohort_analytics(db, cohort_id, current_user)`
5. **Background Task Worker**:
   - `execute_cohort_evaluation_job(cohort_id, user_id)`
   - `execute_batch_risk_stratification_job(patient_ids, risk_type, user_id)`

---

## 7. FHIR R4 Interoperability

### A. Schemas & Mappings
- **FHIR Group**: Maps `PatientCohort` and active members to standard FHIR R4 `Group` (type: `person`, actual: `true`).
- **FHIR RiskAssessment**: Maps `ClinicalRiskAssessment` to FHIR R4 `RiskAssessment` with prediction outcomes, probability/score, and basis references.
- Mappers added to `backend/app/services/fhir_mapper_service.py`:
  - `FHIRGroupMapper`
  - `FHIRRiskAssessmentMapper`
- Service exports added to `backend/app/services/fhir_export_service.py`:
  - `export_cohort_as_fhir_group(db, current_user, cohort_id)`
  - `export_risk_assessment_as_fhir(db, current_user, assessment_id)`
- Endpoints in `backend/app/api/v1/endpoints/fhir.py`:
  - `GET /api/v1/fhir/Group/{cohort_id}`
  - `GET /api/v1/fhir/RiskAssessment/{assessment_id}`

---

## 8. REST API Endpoints (`backend/app/api/v1/endpoints/cohorts.py`)

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `POST` | `/api/v1/cohorts` | Create disease registry / cohort | Clinical / Admin |
| `GET` | `/api/v1/cohorts` | List all cohorts with summary stats | Authenticated Staff |
| `GET` | `/api/v1/cohorts/{cohort_id}` | Get cohort details & criteria | Authenticated Staff |
| `PATCH` | `/api/v1/cohorts/{cohort_id}` | Update cohort details & criteria | Clinical / Admin |
| `DELETE`| `/api/v1/cohorts/{cohort_id}` | Delete cohort | Admin |
| `GET` | `/api/v1/cohorts/{cohort_id}/members` | List patient members in cohort | Authenticated Staff |
| `POST` | `/api/v1/cohorts/{cohort_id}/members` | Manually enroll patient in cohort | Clinical / Admin |
| `DELETE`| `/api/v1/cohorts/{cohort_id}/members/{patient_id}` | Remove patient from cohort | Clinical / Admin |
| `GET` | `/api/v1/cohorts/{cohort_id}/analytics` | Cohort population health analytics | Authenticated Staff |
| `POST` | `/api/v1/patients/{patient_id}/risk-assessments` | Run clinical risk stratification | Clinical / Admin |
| `GET` | `/api/v1/patients/{patient_id}/risk-assessments` | List risk assessments for patient | Patient (own) / Staff |
| `GET` | `/api/v1/risk-assessments/{assessment_id}` | Get risk assessment details | Patient (own) / Staff |
| `POST` | `/api/v1/tasks/cohorts/{cohort_id}/evaluate` | Enqueue background dynamic cohort sync | Clinical / Admin |
| `POST` | `/api/v1/tasks/patients/{patient_id}/stratify-risk` | Enqueue background risk calculation | Clinical / Admin |

---

## 9. Frontend Architecture

1. **Types (`frontend/src/types/index.ts`)**:
   - `CohortType`, `CohortCriteria`, `PatientCohort`, `CohortMembership`, `CohortAnalytics`, `RiskType`, `RiskTier`, `RiskFactor`, `ClinicalRiskAssessment`.
2. **API Client (`frontend/src/api/client.ts`)**:
   - `cohortsApi`: `list`, `get`, `create`, `update`, `delete`, `listMembers`, `addMember`, `removeMember`, `getAnalytics`, `calculateRisk`, `listRiskAssessments`, `getRiskAssessment`.
3. **Cohort & Population Analytics Workspace (`frontend/src/components/cohorts/CohortWorkspace.tsx`)**:
   - Top Header with cohort selector & "➕ New Registry / Cohort" button.
   - Cohort KPI Cards: Total Enrolled, High/Critical Risk Count, Average Risk Score, Active Alert Count.
   - Risk Tier Distribution breakdown (Critical, High, Moderate, Low).
   - Member Patient Grid with real-time risk badges, latest vitals, and one-click patient context switcher.
   - "⚡ Run Risk Stratification" modal with risk type selector and instant results visualization.
   - Clinical factor explanation modal detailing contributing indicators and actionable recommendations.
4. **Dashboard Integration (`frontend/src/pages/DashboardPage.tsx`)**:
   - Add `👥 Population & Risk Analytics` tab.
5. **Frontend Unit Tests (`frontend/src/test/cohorts.test.tsx`)**:
   - Mock API and verify cohort listing, analytics rendering, member table, and risk calculation modal.

---

## 10. Security, RBAC & Patient Isolation Rules
- **Patient Isolation**: Patients querying `/api/v1/patients/{id}/risk-assessments` are strictly restricted to their own record (`user.email == patient.email`).
- **Population Data Protection**: Patients have zero access to `/api/v1/cohorts*` population-level analytics or other patients' members.
- **Zero Raw PHI in Logs**: Structured operational logs record `cohort_id`, `patient_id`, `assessment_id`, `risk_tier`, but never patient names or plain text health identifiers.

---

## 11. Testing & Quality Assurance Plan
- **Backend Test Suite (`backend/tests/test_cohorts_and_risk.py`)**:
  - Cohort CRUD & dynamic criteria filtering.
  - Manual & dynamic membership enrollment.
  - Risk assessment calculation across all 5 risk types.
  - Risk tier and factor weight assertions.
  - Background task worker execution for cohort evaluation and batch risk scoring.
  - FHIR R4 `Group` and `RiskAssessment` serialization.
  - Strict RBAC and cross-patient isolation.
- **Frontend Tests**: `frontend/src/test/cohorts.test.tsx` verifying component interactions.
- **Full Backend Regression**: Baseline 341 passed, 2 skipped.
- **Production Build & Migration Verification**: `npm run build` and `alembic upgrade head --sql`.

---

## 12. Exact Files to Create and Modify

### New Files to Create:
1. `backend/alembic/versions/0013_cohorts_and_risk_stratification.py`
2. `backend/app/models/cohort.py`
3. `backend/app/models/risk_assessment.py`
4. `backend/app/schemas/cohort.py`
5. `backend/app/schemas/risk_assessment.py`
6. `backend/app/ai/risk_provider.py`
7. `backend/app/services/cohort_service.py`
8. `backend/app/api/v1/endpoints/cohorts.py`
9. `backend/tests/test_cohorts_and_risk.py`
10. `frontend/src/components/cohorts/CohortWorkspace.tsx`
11. `frontend/src/test/cohorts.test.tsx`
12. `docs/phase_9_0_11.md`
13. `docs/phase_9_0_11_implementation_plan.md` (this file)

### Existing Files to Modify:
1. `backend/app/models/__init__.py` (export `PatientCohort`, `CohortMembership`, `ClinicalRiskAssessment`)
2. `backend/app/schemas/__init__.py` (export cohort and risk assessment schemas)
3. `backend/app/schemas/task.py` (add `COHORT_ANALYSIS` and `RISK_STRATIFICATION` to `BackgroundTaskType`)
4. `backend/app/schemas/fhir.py` (add `FHIRGroup` and `FHIRRiskAssessment`)
5. `backend/app/services/fhir_mapper_service.py` (add `FHIRGroupMapper` and `FHIRRiskAssessmentMapper`)
6. `backend/app/services/fhir_export_service.py` (add cohort and risk assessment export functions)
7. `backend/app/api/v1/endpoints/fhir.py` (add `Group/{id}` and `RiskAssessment/{id}` endpoints)
8. `backend/app/api/v1/api.py` (include `cohorts.router`)
9. `frontend/src/types/index.ts` (add cohort & risk types)
10. `frontend/src/api/client.ts` (add `cohortsApi`)
11. `frontend/src/pages/DashboardPage.tsx` (add `👥 Population & Risk Analytics` tab)
12. `README.md` (update architecture tree and API endpoints table)

---

## 13. Explicit Non-Goals
- Real-time streaming machine learning model training in the web server (we use deterministic heuristic scoring).
- Integration with proprietary paid population health EHR billing claims vendors.
- Modification of existing care plans, vitals, notes, or media schemas.
