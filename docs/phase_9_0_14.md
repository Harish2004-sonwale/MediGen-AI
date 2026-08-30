# Phase 9.0.14 — Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting Engine

## Overview
Phase 9.0.14 builds a production-grade clinical quality measurement and compliance layer that connects existing MediGen-AI capabilities—patients, encounters, diagnoses, vitals, care plans, discharge protocols, and diagnostic orders—into measurable quality metrics and auditable compliance reports.

The engine supports standardized clinical quality measure (CQM) definitions (e.g. HEDIS, CMS MIPS, NCQA), evaluates patient-level and population-level compliance, detects actionable care gaps, provides gap remediation workflows through care plans and follow-up tasks, and generates immutable audit reports for regulatory and payer compliance.

---

## Key Capabilities

### 1. Standardized CQM & HEDIS/MIPS Measure Definitions
The engine comes pre-configured with 5 core clinical quality measures spanning chronic disease management, care coordination, and patient safety:
1. **`CQM-001-DM-HBA1C`**: Diabetes Glycemic Control ($<8.0\%$) (HEDIS HBD / CMS MIPS #001)
2. **`CQM-002-HTN-BP`**: Controlling High Blood Pressure ($<140/90\text{ mmHg}$) (HEDIS CBP / CMS MIPS #236)
3. **`CQM-003-TOC-MEDREC`**: Post-Discharge Medication Reconciliation (HEDIS TRC / CMS MIPS #046)
4. **`CQM-004-CP-ADHERENCE`**: Care Plan & High-Priority Task Adherence
5. **`CQM-005-CRIT-LAB`**: Closed-Loop Critical Diagnostic Result Signoff

### 2. Deterministic & Offline Patient-Level CQM Evaluation
- Extracts patient diagnoses (encounters), lab results, vital signs, discharge summaries, and care plans.
- Evaluates denominator eligibility, numerator compliance, and exclusions deterministically without external API calls.
- Provides granular clinical evidence payloads for transparent clinical validation.

### 3. Gap-in-Care Detection & Automated Remediation
- Identifies non-compliant patients and generates prioritized `QualityMeasureGap` records (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- One-click remediation: Converts care gaps into actionable `CareTask` items linked to the patient's active `CarePlan`.
- Automatic resolution: Resolves open gaps when subsequent clinical evaluation confirms metric compliance.

### 4. Population Compliance Audits & Immutable Provenance
- Computes aggregate denominator, numerator, and performance rates across patient cohorts or the entire organization.
- Generates cryptographic SHA-256 data provenance hashes over sorted measure performance summaries to guarantee audit integrity and prevent data tampering.
- Stores historical scorecards for payer, regulatory, and quality committee submissions.

### 5. FHIR R4 Interoperability
- **`FHIRMeasure`**: Standard FHIR R4 Measure resource representing CQM metadata, scoring type, and population criteria.
- **`FHIRMeasureReport`**: Standard FHIR R4 MeasureReport resource containing population counts and numerator performance rates.

---

## API Reference

### Quality Measures & Definitions
- `GET /api/v1/quality/measures`: List all active quality measures (supports `?domain=` filtering).
- `GET /api/v1/quality/measures/{measure_id}`: Retrieve detailed measure definition.

### Patient Evaluation & Results
- `POST /api/v1/quality/patients/{patient_id}/evaluate`: Evaluate patient clinical data and synchronize care gaps.
- `GET /api/v1/quality/patients/{patient_id}/results`: List evaluated results for a patient with RBAC isolation.

### Gaps in Care & Remediation
- `GET /api/v1/quality/gaps`: List care gaps (filterable by `patient_id`, `measure_id`, `severity`, `status`).
- `PATCH /api/v1/quality/gaps/{gap_id}`: Update gap status, notes, or due date.
- `POST /api/v1/quality/gaps/{gap_id}/create-care-task`: Convert care gap into an active `CareTask`.

### Compliance Reports & Provenance
- `POST /api/v1/quality/reports/generate`: Synthesize population compliance audit report with provenance hash.
- `GET /api/v1/quality/reports`: List archived compliance audit reports.
- `GET /api/v1/quality/reports/{report_id}`: Retrieve specific report scorecard.

### Asynchronous Tasks & FHIR R4
- `POST /api/v1/quality/tasks/calculate`: Enqueue asynchronous background calculation task.
- `GET /api/v1/fhir/Measure/{measure_id}`: Export CQM as FHIR R4 Measure.
- `GET /api/v1/fhir/MeasureReport/{report_id}`: Export compliance report as FHIR R4 MeasureReport.

---

## Verification & Test Results
- **Backend Tests**: 7 passed (`backend/tests/test_quality_measures.py`), 369 passed full backend regression suite.
- **Frontend Tests**: 32 passed across 12 test suites (`frontend/src/test/quality.test.tsx`).
- **Production Build**: Clean TypeScript and Vite compilation.
- **Alembic Migration**: `0016_clinical_quality_measures_and_compliance.py` verified with `--sql`.
