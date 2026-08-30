# Phase 9.0.16 — Clinical Trials Matching, Biomarker Precision Oncology & Genomic Treatment Eligibility

## Overview
Phase 9.0.16 delivers a deterministic, auditable Clinical Trials Matching, Genomic NGS Biomarker Ingestion, and Precision Oncology Decision-Support platform integrated natively into the MediGen-AI clinical ecosystem.

It empowers clinical oncologists, trial investigators, and molecular tumor boards to evaluate complex clinical eligibility criteria (disease stage, histopathology, genomic mutations, expression levels, copy number alterations, age, prior therapies) against individual patient records with 100% reproducible offline rule execution, cryptographic SHA-256 provenance auditing, and clinician-in-the-loop sign-off governance.

---

## Key Capabilities

### 1. Structured Clinical Trial Protocol & Criteria Modeling
- **`ClinicalTrial`**: Complete representation of clinical trial metadata (NCT number, trial phase, recruitment status, sponsor, condition, intervention class, target age and gender criteria).
- **`TrialEligibilityCriterion`**: Highly expressive inclusion/exclusion criterion modeling supporting categories (`biomarker`, `diagnosis`, `disease_stage`, `age`, `gender`, `prior_therapy`, `lab_threshold`), operators (`=`, `!=`, `>`, `>=`, `<`, `<=`, `IN`, `NOT_IN`, `PRESENT`, `ABSENT`, `CONTAINS`), and explicit required vs optional weighting.

### 2. Multi-Gene NGS Profiling & Molecular Pathology Ingestion
- **`GenomicProfile`**: Next-Generation Sequencing (NGS) molecular pathology panel ingestion tracking specimen type, test name, sequencing platform, performing laboratory, Tumor Mutation Burden (TMB in mut/Mb), Microsatellite Instability (MSI-H vs MSS), and pathologist interpretations.
- **`BiomarkerObservation`**: Granular genomic alteration tracking capturing gene symbol, variant name (e.g. `L858R`, `V600E`, `G12C`), alteration type (`missense_mutation`, `frameshift_deletion`, `amplification`, `expression_level`, `fusion`), Variant Allele Fraction (VAF %), AMP/ASCO/CAP Pathogenicity Tiers (`tier_1_strong_clinical`, `tier_2_potential`, `tier_3_uncertain`, `tier_4_benign`), and Evidence Levels (`FDA_Level_A`, `NCCN_Level_1`).

### 3. Deterministic AI Trial Matching Engine
- **Deterministic & Offline**: 100% reproducible offline matching provider with zero non-deterministic LLM variance, zero GPU requirements, and zero external network calls.
- **Strict Evidence & Missing Data Handling**: Missing or incomplete clinical data strictly evaluates to `INSUFFICIENT_DATA` or `POTENTIAL_MATCH` — never assumed to be eligible without confirmed clinical documentation.
- **Multi-Factor Scorecards**: Evaluates patient age, gender, active diagnoses, cancer staging, and biomarker mutations against trial criteria to produce categorized match states (`MATCHED`, `POTENTIAL_MATCH`, `MANUAL_REVIEW`, `INELIGIBLE`, `INSUFFICIENT_DATA`).
- **Cryptographic Provenance**: Every evaluation payload generates a deterministic SHA-256 hash ensuring tamper-proof auditability for molecular tumor boards and regulatory inspections.

### 4. Precision Oncology Decision Support & Assistive Governance
- **`PrecisionTreatmentEligibility`**: Synthesizes actionable molecular targeted therapy candidates (e.g. 3rd-Gen EGFR TKIs, PARP inhibitors, KRAS G12C inhibitors, Dual Immune Checkpoint inhibitors) mapped to established NCCN guidelines and FDA-approved companion diagnostic labels.
- **Assistive Clinical Decision Support Disclaimer**: Explicitly framed as assistive clinical decision support only; system strictly prohibits autonomous prescription or protocol enrollment.
- **Clinician Review Workflow**: Requires formal physician determination (`confirmed_eligible`, `enrolled_in_trial`, `declined_by_clinician`, `patient_declined`, `approved_for_protocol`, `rejected_by_clinician`) with documented clinical notes.

### 5. FHIR R4 Interoperability
- **`FHIRResearchStudy`**: Bi-directional mapping of clinical trials into FHIR R4 `ResearchStudy` resources.
- **`FHIRObservation`**: Standard molecular pathology FHIR R4 `Observation` mapping with LOINC and HGVS coding.
- **`FHIRDiagnosticReport`**: Genomic profile report exported as FHIR R4 `DiagnosticReport` containing child observation references.

---

## API Reference

### Clinical Trials Management
- `POST /api/v1/trials`: Register a new clinical trial protocol.
- `GET /api/v1/trials`: Query trials with phase, recruitment status, and condition filters.
- `GET /api/v1/trials/{trial_id}`: Retrieve detailed trial protocol and eligibility criteria.
- `POST /api/v1/trials/{trial_id}/criteria`: Add an inclusion or exclusion criterion.

### Genomic Profiles & Biomarkers
- `POST /api/v1/patients/{patient_id}/genomic-profiles`: Ingest an NGS genomic profile report.
- `GET /api/v1/patients/{patient_id}/genomic-profiles`: List patient genomic profiles with RBAC isolation.
- `POST /api/v1/genomic-profiles/{profile_id}/biomarkers`: Add structured biomarker alteration finding.
- `GET /api/v1/genomic-profiles/{profile_id}/biomarkers`: List biomarkers for a profile.

### Trial Matching & Explainability
- `POST /api/v1/trials/{trial_id}/match/{patient_id}`: Execute deterministic matching for a specific trial and patient.
- `POST /api/v1/patients/{patient_id}/trial-matches`: Batch match patient against all active registry trials.
- `GET /api/v1/patients/{patient_id}/trial-matches`: List historical trial matches with status filters.
- `POST /api/v1/trial-matches/{match_id}/review`: Submit clinician review determination and notes.

### Precision Oncology Decision Support
- `POST /api/v1/patients/{patient_id}/precision-eligibility/evaluate`: Synthesize targeted therapy candidates.
- `GET /api/v1/patients/{patient_id}/precision-eligibility`: List synthesized precision therapy options.
- `POST /api/v1/precision-eligibility/{eligibility_id}/review`: Clinician review and protocol sign-off.

### FHIR R4 Endpoints
- `GET /api/v1/fhir/ResearchStudy/{id}`: Export clinical trial as FHIR R4 `ResearchStudy`.
- `GET /api/v1/fhir/Biomarker/{id}`: Export biomarker observation as FHIR R4 `Observation`.
- `GET /api/v1/fhir/GenomicProfile/{id}`: Export genomic profile as FHIR R4 `DiagnosticReport`.

---

## Testing & Quality Assurance
- **Database Migration**: `backend/alembic/versions/0018_clinical_trials_genomics_precision_oncology.py`.
- **Backend Integration Suite**: `backend/tests/test_trials_genomics_precision.py` (8 test cases covering CRUD, ingestion, deterministic matching, missing data, numeric thresholds, clinician review, RBAC patient isolation, FHIR R4 exports, and async tasks).
- **Frontend Vitest Suite**: `frontend/src/test/trials.test.tsx` (6 test cases covering workspace rendering, scorecards, explainability modals with SHA-256 hash, clinician review sign-offs, NGS genomic tables, and precision oncology decision support).
