# Phase 9.0.11 — Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification

## 1. Overview
Phase 9.0.11 delivers Population Health Intelligence and Longitudinal Clinical Risk Stratification within MediGen-AI. It empowers clinical directors, attending physicians, and care managers to manage dynamic patient disease registries (e.g., Chronic Hypertension, Uncontrolled Diabetes, Post-Inpatient Readmission Watch, Sepsis Vulnerability), calculate multi-factorial longitudinal clinical risk scores, and track aggregate population health metrics.

---

## 2. Key Architecture Components

### A. Patient Cohorts & Disease Registries
- **Models**:
  - `PatientCohort` (`patient_cohorts` table): Defines cohort name, description, category (`disease_registry`, `risk_watch_list`, `post_op_monitoring`, `quality_measure`, `custom_cohort`), inclusion rules in `criteria_json` (age range, condition keywords, vital thresholds, risk tiers), and dynamic enrollment indicator.
  - `CohortMembership` (`cohort_memberships` table): Manages patient-to-cohort link, status (`active`, `graduated`, `excluded`), notes, and unique constraint on `(cohort_id, patient_id)`.
- **Dynamic Criteria Synchronization**:
  - Background worker & service rule engine evaluate patient demographics, encounters, care plans, vitals, and active CDS alerts to automatically enroll matching patients and graduate non-matching patients.

### B. Multi-Factorial Clinical Risk Stratification Engine
- **Model**: `ClinicalRiskAssessment` (`clinical_risk_assessments` table).
- **Risk Types**:
  - `readmission_30d`: 30-day hospital readmission risk.
  - `cardiovascular_decompensation`: 90-day acute cardiovascular/heart failure event risk.
  - `clinical_deterioration`: Inpatient deterioration, sepsis escalation, or ICU transfer risk.
  - `medication_adherence`: Medication non-compliance or therapy discontinuation likelihood.
  - `general_mortality`: 1-year multi-morbid mortality vulnerability index.
- **Provider Architecture**:
  - `BaseRiskStratificationProvider` & `MockRiskStratificationProvider`: Deterministic clinical heuristic algorithm calculating quantitative score (0.0 to 100.0), Risk Tier (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`), structured list of contributing factors, and prioritized mitigation actions.
  - 100% offline, zero-GPU, zero external API keys.

### C. Population Health Analytics
- Real-time aggregate indicator calculation across cohort members:
  - Enrolled member count & risk tier distributions.
  - Mean risk score across cohort.
  - High/Critical risk patient volume.
  - Active CDS alert volume.
  - Active care plan coverage and overdue follow-up task ratios.

### D. FHIR R4 Interoperability
- Maps `PatientCohort` $\rightarrow$ standard FHIR R4 `Group` with member list.
- Maps `ClinicalRiskAssessment` $\rightarrow$ standard FHIR R4 `RiskAssessment` with prediction concepts, probability decimals, qualitative risk codes, and mitigation summaries.
- Endpoints:
  - `GET /api/v1/fhir/Group/{cohort_id}`
  - `GET /api/v1/fhir/RiskAssessment/{assessment_id}`

### E. Frontend Cohort & Population Risk Workspace
- `CohortWorkspace.tsx` in `frontend/src/components/cohorts/` integrated into `DashboardPage.tsx` under `👥 Population & Risk Analytics`.
- Features:
  - Cohort registry selector & creation modal.
  - KPI Analytics cards and risk tier distribution bar.
  - Enrolled patients table with real-time risk scores and tier badges.
  - Actionable risk stratification calculation modal and clinical factor breakdown modal.

---

## 3. Database Migration
- **Migration**: `0013_cohorts_and_risk_stratification.py`
- Chain: `0001` -> `...` -> `0012_care_plans_and_tasks` -> `0013_cohorts_and_risk_stratification`.
- Creates `patient_cohorts`, `cohort_memberships`, `clinical_risk_assessments` tables, foreign keys, and indexes.

---

## 4. Verification Results
- **Backend Focused Tests**: 7 passed (`test_cohorts_and_risk.py`).
- **Backend Full Regression**: 348 passed, 2 skipped (100% pass across all 41 test files).
- **Frontend Unit Tests**: 22 passed across 9 test files (`cohorts.test.tsx`, `care.test.tsx`, etc.).
- **Frontend Production Build**: Clean build passed (`tsc && vite build`, `269 kB`, gzip `70 kB`).
- **Alembic Migration SQL**: `upgrade head --sql` validated for PostgreSQL.
- **Git Diff & Formatting**: `git diff --check` returned 0 errors.
- **Security & Secrets Check**: Clean, zero credentials, `.env` files, or runtime secrets.
