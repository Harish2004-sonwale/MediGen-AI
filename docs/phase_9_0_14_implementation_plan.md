# Phase 9.0.14 Implementation Plan: Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting Engine

## Executive Summary & Background Context
MediGen-AI has built a comprehensive clinical care platform across patient management, clinical encounters, diagnostic imaging, automated note synthesis, vitals telemetry, CDS alerting, longitudinal care plans, cohort risk registries, transitions of care/discharge, computerized physician order entry (CPOE), and closed-loop diagnostic results.

**Phase 9.0.14** introduces a production-grade **Clinical Quality Measurement, HEDIS/MIPS Compliance & Audit Reporting Engine**. This layer evaluates patient and population data against standardized quality measure definitions (diabetes control, hypertension control, post-discharge medication reconciliation, care plan adherence, critical lab follow-up), identifies clinical **Gaps in Care**, auto-links remediation tasks into the existing care workflow, and generates immutable, auditable compliance reports with full data provenance.

---

## User Review Required

> [!IMPORTANT]
> **Deterministic Calculation & Clinical Provenance**:
> - All CQM calculations run deterministically against verified clinical entities in the database (encounters, diagnostic results, vitals, care plans, discharge records) with 0 external API dependencies.
> - Source clinical entities are referenced in `evidence_json` for end-to-end auditability and HEDIS/MIPS provenance verification.

---

## Proposed System Architecture

### 1. Database Layer (Migration `0016_clinical_quality_measures_and_compliance.py`)
- **`quality_measures`**:
  - `id`, `measure_id` (e.g. `CQM-001-DM-HBA1C`, `CQM-002-HTN-BP`, `CQM-003-TOC-MEDREC`, `CQM-004-CP-ADHERENCE`, `CQM-005-CRIT-LAB`), `title`, `description`, `version`, `domain`, `hedis_mips_reference`, `denominator_criteria_json`, `numerator_criteria_json`, `exclusion_criteria_json`, `target_compliance_rate`, `is_active`, `created_at`, `updated_at`.
- **`quality_measure_results`**:
  - `id`, `result_id` (`QMR-YYYYMMDD-HEX`), `measure_id` (FK), `patient_id` (FK), `measurement_period_start`, `measurement_period_end`, `is_eligible`, `is_excluded`, `exclusion_reason`, `is_numerator_compliant`, `compliance_status` (`compliant`, `non_compliant`, `excluded`, `missing_data`), `evidence_json`, `gap_reason`, `remediation_action`, `calculated_by_user_id` (FK, nullable), `calculated_at`, `created_at`, `updated_at`.
- **`quality_measure_gaps`**:
  - `id`, `gap_id` (`QMG-YYYYMMDD-HEX`), `result_id` (FK), `patient_id` (FK), `measure_id` (FK), `gap_type`, `severity` (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`), `status` (`open`, `in_remediation`, `resolved`, `dismissed`), `gap_description`, `missing_data_elements`, `recommended_action`, `due_date`, `linked_care_task_id` (FK to `care_tasks`, nullable), `created_at`, `resolved_at`.
- **`quality_measure_reports`**:
  - `id`, `report_id` (`QRP-YYYYMMDD-HEX`), `title`, `reporting_period_start`, `reporting_period_end`, `report_scope` (`organization`, `provider`, `cohort`, `measure`), `total_eligible_population`, `total_numerator_compliant`, `overall_performance_rate`, `measure_summaries_json`, `audit_metadata_json`, `generated_by_user_id` (FK, nullable), `generated_at`, `created_at`.

### 2. Deterministic AI / CQM Calculation Engine (`quality_provider.py`)
- Standardized representative measures:
  1. `CQM-001-DM-HBA1C` (HEDIS HBD / MIPS #001): Diabetes Glycemic Control ($<8.0\%$).
  2. `CQM-002-HTN-BP` (HEDIS CBP / MIPS #236): Controlling High Blood Pressure ($<140/90\text{ mmHg}$).
  3. `CQM-003-TOC-MEDREC` (HEDIS TRC / MIPS #046): Multi-Disciplinary Post-Discharge Medication Reconciliation.
  4. `CQM-004-CP-ADHERENCE`: Care Plan & High-Priority Task Completion Rate.
  5. `CQM-005-CRIT-LAB`: Closed-Loop Panic Critical Diagnostic Result Review & Signoff.
- Evaluates eligibility, denominator inclusion, exclusions, numerator compliance, and structured clinical evidence.

### 3. Service Layer (`quality_service.py`)
- Seed default measures if not present.
- Patient-level and population-level measure evaluation.
- Gap-in-care lifecycle and integration with `CareTask` for remediation.
- Audit report synthesis and data provenance tracking.
- Background worker integration for `QUALITY_MEASURE_CALCULATION`, `QUALITY_GAP_ANALYSIS`, and `QUALITY_REPORT_GENERATION`.

### 4. FHIR R4 Interoperability
- **`Measure`**: Represents quality measure metadata, scoring criteria, and clinical domain.
- **`MeasureReport`**: Represents individual or aggregate performance results, numerator/denominator counts, and evaluated patient resources.
- Endpoints: `GET /api/v1/fhir/Measure/{measure_id}` and `GET /api/v1/fhir/MeasureReport/{report_id}`.

### 5. REST API Endpoints (`backend/app/api/v1/endpoints/quality.py`)
- `GET /api/v1/quality/measures`: List quality measures.
- `GET /api/v1/quality/measures/{measure_id}`: Get measure details.
- `POST /api/v1/quality/patients/{patient_id}/evaluate`: Evaluate all quality measures for patient.
- `GET /api/v1/quality/patients/{patient_id}/results`: List quality results for patient.
- `GET /api/v1/quality/gaps`: List gaps in care with status and severity filters.
- `PATCH /api/v1/quality/gaps/{gap_id}`: Update gap status or remediation notes.
- `POST /api/v1/quality/gaps/{gap_id}/create-care-task`: Auto-create linked CareTask for gap remediation.
- `POST /api/v1/quality/reports/generate`: Generate population quality compliance audit report.
- `GET /api/v1/quality/reports`: List generated compliance reports.
- `GET /api/v1/quality/reports/{report_id}`: Retrieve report details and audit metadata.
- `POST /api/v1/tasks/quality/calculate`: Enqueue background quality calculation job.

### 6. Frontend Workspace (`QualityMeasuresWorkspace.tsx`)
- Integrated in `DashboardPage.tsx` under tab `📊 Clinical Quality & Compliance`.
- Overview KPIs: Overall compliance rate %, total eligible patients, compliant patients, open gaps in care.
- Scorecard grid with performance vs. target bars, numerator/denominator stats, and evidence inspector modal.
- Prioritized Gaps in Care feed with "Remediate / Create Care Task" actions.
- Audit Reports archive with audit provenance inspection.

---

## Proposed Changes

### Database Layer
#### [NEW] [0016_clinical_quality_measures_and_compliance.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/alembic/versions/0016_clinical_quality_measures_and_compliance.py)
#### [NEW] [quality.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/quality.py)
#### [MODIFY] [__init__.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/__init__.py)

---

### Schemas Layer
#### [NEW] [quality.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/schemas/quality.py)
#### [MODIFY] [task.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/schemas/task.py)
#### [MODIFY] [fhir.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/schemas/fhir.py)
#### [MODIFY] [__init__.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/schemas/__init__.py)

---

### AI & Service Layer
#### [NEW] [quality_provider.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/ai/quality_provider.py)
#### [NEW] [quality_service.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/services/quality_service.py)
#### [MODIFY] [fhir_mapper_service.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/services/fhir_mapper_service.py)
#### [MODIFY] [fhir_export_service.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/services/fhir_export_service.py)

---

### API Layer
#### [NEW] [quality.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/api/v1/endpoints/quality.py)
#### [MODIFY] [fhir.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/api/v1/endpoints/fhir.py)
#### [MODIFY] [api.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/api/v1/api.py)

---

### Frontend Layer
#### [MODIFY] [index.ts](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/types/index.ts)
#### [MODIFY] [client.ts](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/api/client.ts)
#### [NEW] [QualityMeasuresWorkspace.tsx](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/components/quality/QualityMeasuresWorkspace.tsx)
#### [MODIFY] [DashboardPage.tsx](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/pages/DashboardPage.tsx)

---

### Testing & Documentation
#### [NEW] [test_quality_measures.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/tests/test_quality_measures.py)
#### [NEW] [quality.test.tsx](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/test/quality.test.tsx)
#### [NEW] [phase_9_0_14.md](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/docs/phase_9_0_14.md)
#### [MODIFY] [README.md](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/README.md)

---

## Verification Plan
- Focused backend tests: `pytest backend/tests/test_quality_measures.py -v`
- Full backend regression: `pytest backend/tests -q` (Target: 369+ passing)
- Frontend unit tests: `npm.cmd test -- --run` (Target: 31+ passing across 12 suites)
- Frontend production build: `npm.cmd run build`
- Alembic migration 0016 SQL validation: `alembic -c backend/alembic.ini upgrade head --sql`
- Clean git diff and check validation
