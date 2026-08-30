# Phase 9.0.16 Implementation Plan — Clinical Trials Matching, Biomarker Precision Oncology & Genomic Treatment Eligibility

## 1. Executive Architecture Overview
Phase 9.0.16 establishes a deterministic, auditable clinical trial matching and precision oncology decision-support engine for MediGen-AI. The engine connects structured patient clinical context (diagnoses, disease staging, age, sex, prior therapies, laboratory results) and patient molecular genomic profiles (biomarkers, variant alterations, expression levels, copy number variations) with structured clinical trial eligibility criteria and biomarker-driven therapy rules.

### Core Architectural Principles:
1. **100% Deterministic & Reproducible**: Multi-criteria matching engine evaluates patient data against trial criteria strictly through deterministic Boolean, numeric threshold, set inclusion, and presence/absence operations.
2. **Explainable Triage Outcomes**: Every evaluation criterion evaluates to `PASS`, `FAIL`, or `UNKNOWN`. The overall trial match evaluates to `MATCHED`, `POTENTIAL_MATCH`, `INELIGIBLE`, `INSUFFICIENT_DATA`, or `MANUAL_REVIEW`. Missing data is never assumed to be satisfied.
3. **Assistive Clinical Decision Support (CDS) Boundaries**: The engine generates precision treatment eligibility assessments as non-autonomous decision support only. It never auto-prescribes, auto-orders, or finalizes oncology treatments without explicit clinician review, documented provenance, and approval.
4. **End-to-End Interoperability (FHIR R4)**: Full mapping and export for `FHIRResearchStudy`, `FHIRObservation` (genomic biomarkers / molecular findings), and `FHIRDiagnosticReport` (genomic profiling panels).
5. **Zero External API / Zero GPU Dependency**: Pure offline Python evaluation with cryptographic SHA-256 provenance hashing of matching evidence.

---

## 2. Database Models & Schema Design (`backend/app/models/trials.py`)

We create 6 core relational models in PostgreSQL:

### A. `ClinicalTrial` (`clinical_trials`)
- `id`: Integer primary key
- `trial_id`: String(64) unique identifier (e.g. `TRIAL-LUNG-001`, `NCT04567890`)
- `nct_number`: String(32) optional external identifier (e.g. `NCT04567890`)
- `title`: String(255) trial title
- `official_title`: Text
- `sponsor`: String(150) trial sponsor / lead institution
- `phase`: String(30) (`phase_1`, `phase_2`, `phase_3`, `phase_4`, `early_phase_1`)
- `status`: String(30) (`recruiting`, `active_not_recruiting`, `enrolling_by_invitation`, `completed`, `suspended`, `terminated`)
- `disease_condition`: String(150) target malignancy or condition (e.g. `Non-Small Cell Lung Cancer`, `Breast Cancer`)
- `intervention_name`: String(255) investigational agent or regimen
- `intervention_type`: String(50) (`targeted_therapy`, `immunotherapy`, `chemotherapy`, `cell_therapy`, `combination`)
- `location_sites_json`: JSON list of trial sites / centers
- `min_age_years`: Integer minimum age
- `max_age_years`: Integer maximum age
- `target_gender`: String(20) (`all`, `female`, `male`)
- `summary`: Text clinical overview
- `inclusion_criteria_text`: Text
- `exclusion_criteria_text`: Text
- `contact_email`: String(120)
- `contact_phone`: String(50)
- `is_active`: Boolean
- `version`: String(20)
- `created_at`: DateTime(timezone=True)
- `updated_at`: DateTime(timezone=True)

### B. `TrialEligibilityCriterion` (`trial_eligibility_criteria`)
- `id`: Integer primary key
- `criterion_id`: String(64) unique identifier (e.g. `CRIT-LUNG-001-EGFR`)
- `trial_id`: Integer foreign key -> `clinical_trials.id` (ON DELETE CASCADE)
- `category`: String(50) (`biomarker`, `diagnosis`, `disease_stage`, `age`, `performance_status`, `prior_therapy`, `laboratory_value`, `organ_function`, `contraindication`)
- `criterion_type`: String(20) (`inclusion`, `exclusion`)
- `field_name`: String(80) target clinical field (e.g. `gene_symbol`, `variant_name`, `stage`, `ecog_score`, `hba1c`, `platelet_count`, `prior_drug`)
- `operator`: String(20) (`==`, `!=`, `>`, `>=`, `<`, `<=`, `IN`, `NOT_IN`, `PRESENT`, `ABSENT`)
- `expected_value_str`: String(255)
- `expected_value_num`: Float
- `expected_value_json`: JSON
- `unit_of_measure`: String(30)
- `is_required`: Boolean (default True)
- `description`: Text human-readable explanation
- `created_at`: DateTime(timezone=True)

### C. `GenomicProfile` (`genomic_profiles`)
- `id`: Integer primary key
- `profile_id`: String(64) unique identifier (e.g. `GEN-PROF-001`)
- `patient_id`: Integer foreign key -> `patients.id` (ON DELETE RESTRICT)
- `specimen_type`: String(80) (e.g. `tumor_tissue_biopsy`, `cfDNA_liquid_biopsy`, `bone_marrow_aspirate`)
- `specimen_collected_at`: DateTime(timezone=True)
- `test_name`: String(150) (e.g. `Comprehensive NGS Solid Tumor Panel (500 Genes)`, `Liquid Biopsy ctDNA Assay`)
- `sequencing_platform`: String(100) (e.g. `Illumina NovaSeq 6000`, `Ion Torrent Genexus`)
- `performing_lab`: String(150) (e.g. `MediGen Precision Genomics Core`, `Foundation Medicine`)
- `accession_number`: String(80)
- `tumor_mutation_burden`: Float (mut/Mb)
- `microsatellite_instability_status`: String(30) (`MSI-H`, `MSI-L`, `MSS`)
- `overall_interpretation`: Text
- `status`: String(30) (`preliminary`, `final`, `amended`)
- `created_at`: DateTime(timezone=True)
- `updated_at`: DateTime(timezone=True)

### D. `BiomarkerObservation` (`biomarker_observations`)
- `id`: Integer primary key
- `observation_id`: String(64) unique identifier (e.g. `BM-OBS-001`)
- `profile_id`: Integer foreign key -> `genomic_profiles.id` (ON DELETE CASCADE)
- `patient_id`: Integer foreign key -> `patients.id` (ON DELETE RESTRICT)
- `gene_symbol`: String(50) (e.g. `EGFR`, `ALK`, `BRAF`, `KRAS`, `HER2`, `BRCA1`, `BRCA2`, `PD-L1`, `ROS1`, `MET`, `RET`, `NTRK1`)
- `variant_name`: String(100) (e.g. `L858R`, `T790M`, `V600E`, `G12C`, `EML4-ALK Fusion`, `Exon 19 Deletion`)
- `alteration_type`: String(50) (`missense_mutation`, `deletion`, `insertion`, `frameshift`, `gene_fusion`, `copy_number_amplification`, `expression_level`, `loss_of_function`)
- `hgvs_notation`: String(120) (e.g. `c.2573T>G (p.Leu858Arg)`)
- `chromosome`: String(10)
- `genomic_position`: String(50)
- `reference_allele`: String(50)
- `alternate_allele`: String(50)
- `zygosity`: String(30) (`heterozygous`, `homozygous`, `hemizygous`)
- `variant_allele_fraction`: Float (VAF %)
- `pathogenicity`: String(40) (`tier_1_strong_clinical`, `tier_2_potential_clinical`, `tier_3_unknown_significance`, `pathogenic`, `likely_pathogenic`, `benign`)
- `evidence_level`: String(20) (`FDA_Level_A`, `Standard_Level_B`, `Investigational_Level_C`, `Preclinical_Level_D`)
- `clinical_significance`: Text
- `numeric_expression_value`: Float (e.g. PD-L1 Tumor Proportion Score `TPS 75%`)
- `expression_unit`: String(20) (`%`, `copies/uL`, `FPKM`)
- `detected_at`: DateTime(timezone=True)
- `created_at`: DateTime(timezone=True)

### E. `TrialMatch` (`trial_matches`)
- `id`: Integer primary key
- `match_id`: String(64) unique identifier (e.g. `TMATCH-001`)
- `trial_id`: Integer foreign key -> `clinical_trials.id` (ON DELETE RESTRICT)
- `patient_id`: Integer foreign key -> `patients.id` (ON DELETE RESTRICT)
- `match_status`: String(30) (`MATCHED`, `POTENTIAL_MATCH`, `INELIGIBLE`, `INSUFFICIENT_DATA`, `MANUAL_REVIEW`)
- `match_score`: Float (0.0 to 100.0)
- `matched_criteria_json`: JSON list of satisfied criteria with patient evidence
- `failed_criteria_json`: JSON list of failed criteria with patient evidence
- `unknown_criteria_json`: JSON list of indeterminate criteria needing manual clinical chart review
- `overall_explanation`: Text structured synthesis
- `provenance_hash`: String(64) SHA-256 hash of patient snapshot & trial criteria
- `algorithm_version`: String(20)
- `clinician_review_status`: String(30) (`pending_review`, `confirmed_eligible`, `declined_by_clinician`, `enrolled_in_trial`, `patient_declined`)
- `reviewed_by_user_id`: Integer foreign key -> `users.id` (ON DELETE SET NULL)
- `review_notes`: Text
- `reviewed_at`: DateTime(timezone=True)
- `created_at`: DateTime(timezone=True)
- `updated_at`: DateTime(timezone=True)

### F. `PrecisionTreatmentEligibility` (`precision_treatment_eligibilities`)
- `id`: Integer primary key
- `eligibility_id`: String(64) unique identifier (e.g. `PREC-ELIG-001`)
- `patient_id`: Integer foreign key -> `patients.id` (ON DELETE RESTRICT)
- `gene_symbol`: String(50)
- `variant_name`: String(100)
- `recommended_intervention`: String(255) (e.g. `Osimertinib (Tagrisso)`, `Sotorasib (Lumakras)`, `Pembrolizumab (Keytruda)`, `Olaparib (Lynparza)`)
- `drug_class`: String(100) (e.g. `3rd-Gen EGFR Tyrosine Kinase Inhibitor`, `KRAS G12C Inhibitor`, `Anti-PD-1 Immune Checkpoint Inhibitor`, `PARP Inhibitor`)
- `indication`: String(150) (e.g. `EGFR L858R / Exon 19 Del Metastatic NSCLC`)
- `eligibility_status`: String(30) (`ELIGIBLE`, `NOT_ELIGIBLE`, `INSUFFICIENT_DATA`, `MANUAL_REVIEW`)
- `evidence_source`: String(100) (e.g. `NCCN Guidelines v2026.1 / FDA Label / OncoKB Level 1`)
- `supporting_observations_json`: JSON list of detected biomarkers & diagnostic findings
- `contraindicating_observations_json`: JSON list of resistance mutations or organ contraindications (e.g. `EGFR T790M / C797S resistance mutation detected`, `Severe Hepatic Impairment`)
- `unknown_factors_json`: JSON list of missing safety parameters (e.g. `Recent Liver Function Test missing`)
- `provenance_hash`: String(64) SHA-256 hash
- `clinician_review_status`: String(30) (`pending_review`, `approved_for_protocol`, `rejected_by_clinician`)
- `reviewed_by_user_id`: Integer foreign key -> `users.id` (ON DELETE SET NULL)
- `review_notes`: Text
- `reviewed_at`: DateTime(timezone=True)
- `created_at`: DateTime(timezone=True)

---

## 3. Deterministic Matching Engine Architecture (`backend/app/ai/trial_matching_provider.py`)

### Matching Rule Matrix:
1. **Exclusion Criteria**:
   - If ANY exclusion criterion evaluates to `FAIL` (i.e. the patient possesses the excluded condition, resistance biomarker, or prohibited prior therapy) -> Match status is **`INELIGIBLE`**.
2. **Inclusion Criteria**:
   - If ALL inclusion criteria evaluate to `PASS` and NO exclusions fail -> Match status is **`MATCHED`** (Score = 100.0).
   - If NO criteria fail, but $\ge 1$ required inclusion criteria are `UNKNOWN` due to missing patient data -> Match status is **`POTENTIAL_MATCH`** or **`MANUAL_REVIEW`** (Score proportional to confirmed passes / total criteria).
   - If all critical biomarker or stage criteria are missing -> Match status is **`INSUFFICIENT_DATA`**.
   - If ANY inclusion criterion evaluates to `FAIL` (e.g. patient stage is II but trial requires Stage IV, or patient has KRAS G12D but trial requires KRAS G12C) -> Match status is **`INELIGIBLE`**.

### Standardized Biomarker & Precision Oncology Knowledge Base:
- `EGFR (L858R, Exon 19 Deletion, Exon 20 Insertion, T790M, C797S)` -> `Osimertinib`, `Amivantamab`, `Mobocertinib`.
- `ALK (EML4-ALK Fusion)` -> `Alectinib`, `Brigatinib`, `Lorlatinib`.
- `KRAS (G12C)` -> `Sotorasib`, `Adagrasib`.
- `BRAF (V600E)` -> `Dabrafenib + Trametinib`, `Encorafenib`.
- `HER2 / ERBB2 (Amplification, Exon 20 Insertion)` -> `Trastuzumab Deruxtecan (T-DXd)`, `Tucatinib`.
- `BRCA1 / BRCA2 (Germline/Somatic Pathogenic Mutation)` -> `Olaparib`, `Talazoparib`.
- `PD-L1 (TPS >= 50% vs TPS 1-49% vs TPS < 1%)` -> `Pembrolizumab Monotherapy` vs `Chemoimmunotherapy`.
- `MSI-H / dMMR / TMB >= 10 mut/Mb` -> `Pembrolizumab / Dostarlimab Tumor-Agnostic Therapy`.
- `ROS1 (Fusion)` -> `Crizotinib`, `Entrectinib`.

---

## 4. REST API Endpoint Design (`backend/app/api/v1/endpoints/trials.py`)

| Method | Route | Description | RBAC |
|---|---|---|---|
| `POST` | `/api/v1/trials` | Create clinical trial definition | Doctor, Admin |
| `GET` | `/api/v1/trials` | List active clinical trials (with filters) | Doctor, Patient, Admin |
| `GET` | `/api/v1/trials/{trial_id}` | Get trial details & eligibility criteria | Doctor, Patient, Admin |
| `PATCH` | `/api/v1/trials/{trial_id}` | Update trial details | Doctor, Admin |
| `POST` | `/api/v1/trials/{trial_id}/criteria` | Add structured eligibility criterion | Doctor, Admin |
| `GET` | `/api/v1/trials/{trial_id}/criteria` | List eligibility criteria for trial | Doctor, Patient, Admin |
| `POST` | `/api/v1/patients/{patient_id}/genomic-profiles` | Upload genomic profile panel | Doctor, Admin |
| `GET` | `/api/v1/patients/{patient_id}/genomic-profiles` | List genomic profiles for patient | Doctor, Patient, Admin |
| `POST` | `/api/v1/genomic-profiles/{profile_id}/biomarkers` | Add structured biomarker observation | Doctor, Admin |
| `GET` | `/api/v1/genomic-profiles/{profile_id}/biomarkers` | List biomarker observations in profile | Doctor, Patient, Admin |
| `POST` | `/api/v1/trials/{trial_id}/match/{patient_id}` | Deterministically match trial for patient | Doctor, Admin |
| `POST` | `/api/v1/patients/{patient_id}/trial-matches` | Run batch trial matching for patient | Doctor, Admin |
| `GET` | `/api/v1/patients/{patient_id}/trial-matches` | List trial match scorecards for patient | Doctor, Patient, Admin |
| `POST` | `/api/v1/trial-matches/{match_id}/review` | Clinician review & sign-off on trial match | Doctor, Admin |
| `POST` | `/api/v1/patients/{patient_id}/precision-eligibility/evaluate` | Synthesize precision treatment eligibility | Doctor, Admin |
| `GET` | `/api/v1/patients/{patient_id}/precision-eligibility` | List precision treatment eligibility | Doctor, Patient, Admin |
| `POST` | `/api/v1/tasks/patients/{patient_id}/trial-matching` | Dispatch async trial matching background task | Doctor, Admin |

---

## 5. FHIR R4 Interoperability
1. **`FHIRResearchStudy`**: Export `ClinicalTrial` as standard FHIR R4 ResearchStudy resource (`id`, `status`, `title`, `condition`, `sponsor`, `enrollment`, `period`).
2. **`FHIRObservation`**: Export `BiomarkerObservation` as FHIR R4 Observation with category `laboratory` / `genomics` (`code`, `valueCodeableConcept`, `valueQuantity`, `interpretation`, `component`).
3. **`FHIRDiagnosticReport`**: Export `GenomicProfile` as FHIR R4 DiagnosticReport with category `GE` (Genetics) referencing child biomarker observations.
4. **Endpoints**:
   - `GET /api/v1/fhir/ResearchStudy/{trial_id}`
   - `GET /api/v1/fhir/Observation/{biomarker_id}`
   - `GET /api/v1/fhir/DiagnosticReport/{profile_id}`

---

## 6. Frontend Workspace Design (`frontend/src/components/trials/TrialsPrecisionWorkspace.tsx`)
- **Clinical Trials Registry**: Searchable repository of active trials with filters by phase, condition, target biomarker, and recruiting status.
- **Genomic Profiles & Biomarker Explorer**: Structured NGS panel view showing gene variants, VAF %, pathogenicity classification (Tier I-IV), TMB, and MSI status.
- **Patient Trial Matching Hub**: Match scorecards displaying `MATCHED`, `POTENTIAL_MATCH`, `INELIGIBLE`, and `MANUAL_REVIEW` statuses with full explainability breakdowns (matched criteria vs failed criteria vs missing criteria).
- **Precision Treatment Decision Support**: Assistive therapy recommendations displaying molecular indication, drug class, level of evidence, contraindication checks, and clinician review controls.
- **Prominent Decision Support Disclaimers**: Bold visual disclaimers reminding clinicians that all recommendations require clinical correlation and physician order authorization.

---

## 7. Testing & Verification Strategy
- **Backend Tests (`backend/tests/test_trials_genomics_precision.py`)**:
  - Trial & criteria CRUD.
  - Genomic profile & biomarker observation ingestion.
  - Exact biomarker positive match (e.g. EGFR L858R).
  - Failed biomarker criterion (e.g. ALK negative).
  - Missing biomarker criterion -> `POTENTIAL_MATCH` / `INSUFFICIENT_DATA`.
  - Numeric threshold criteria (e.g. PD-L1 TPS >= 50%).
  - Age, disease condition, staging, prior therapy, and exclusion criteria logic.
  - Overall `MATCHED`, `INELIGIBLE`, `MANUAL_REVIEW` states.
  - Provenance SHA-256 hash stability.
  - Clinician review and status signoff.
  - Precision treatment eligibility synthesis & contraindication detection.
  - Patient isolation RBAC checks.
  - FHIR R4 exports (`ResearchStudy`, `Observation`, `DiagnosticReport`).
  - Background task execution.
- **Frontend Unit Tests (`frontend/src/test/trials.test.tsx`)**:
  - Trials catalog rendering and filter interactions.
  - Genomic profile and biomarker panel display.
  - Match cards and explainability drawer.
  - Clinician review actions.
- **Full Regressions**:
  - `pytest backend/tests -q` (all ~385+ tests).
  - `npm test -- --run` (all ~37+ frontend tests).
  - `npm run build` (zero TypeScript errors).
  - `alembic upgrade head --sql` (verified migration `0018_clinical_trials_genomics_precision_oncology.py`).
