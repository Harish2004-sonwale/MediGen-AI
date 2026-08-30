# Phase 9.0.18 Implementation Plan — Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow

## 1. Executive Summary & Safety Policy
Phase 9.0.18 establishes a clinical-grade medical imaging and radiology coordination platform within MediGen-AI.
- **Safety Policy**: Assistive clinical decision support only. AI never diagnoses, finalizes reports, or orders treatment. All AI findings and draft reports remain `DRAFT` / `AI_ASSISTED` / `RADIOLOGIST_REVIEW` until an authorized clinician signs off.
- **Critical Findings**: Trigger immediate structured `ClinicalAlert` with disclaimer: `"POTENTIALLY CRITICAL AI-ASSISTED FINDING — REQUIRES IMMEDIATE CLINICIAN REVIEW."`

---

## 2. Architecture & Data Model

### Database Migration `0020_medical_imaging_and_radiology_workflow.py`
1. `imaging_studies`:
   - `study_id`, `patient_id`, `encounter_id`, `order_id`, `modality`, `body_site`, `study_description`, `accession_number`, `study_datetime`, `performing_department`, `referring_provider`, `status`, `source`, `external_identifier`, `metadata_json`, `provenance_hash`.
2. `imaging_assets`:
   - `asset_id`, `study_id`, `series_instance_uid`, `sop_instance_uid`, `series_number`, `instance_number`, `series_description`, `modality`, `body_site`, `mime_type`, `file_size_bytes`, `storage_path`, `thumbnail_storage_path`, `image_dimensions`, `dicom_metadata_json`, `provenance_hash`.
3. `imaging_findings`:
   - `finding_id`, `study_id`, `asset_id`, `patient_id`, `finding_type`, `anatomical_location`, `laterality`, `severity`, `confidence_score`, `is_critical`, `finding_nature` (`OBSERVED_FACT`, `AI_GENERATED_FINDING`, `CLINICIAN_CONFIRMED_FINDING`), `description`, `recommendation`, `bounding_box_json`, `clinician_review_status`, `reviewed_by_user_id`, `reviewed_at`, `review_notes`, `provenance_hash`.
4. `radiology_reports`:
   - `report_id`, `study_id`, `patient_id`, `encounter_id`, `order_id`, `status` (`DRAFT`, `AI_ASSISTED`, `RADIOLOGIST_REVIEW`, `FINALIZED`, `AMENDED`), `clinical_indication`, `technique`, `comparison_studies`, `findings`, `impression`, `recommendations`, `critical_findings_summary`, `is_critical`, `ai_assistance_metadata_json`, `author_user_id`, `signed_by_user_id`, `signed_at`, `amendment_reason`, `amended_from_report_id`, `provenance_hash`.

---

## 3. AI Imaging & Multimodal Provider
- `backend/app/ai/imaging_provider.py`:
  - `BaseImagingAIProvider` and `MockImagingAIProvider`.
  - Deterministic evaluation based on modality, body site, clinical history, prior studies, vitals, lab results, and CDS alerts.
  - Generates structured `ImagingFinding` and draft `RadiologyReport`.
  - Distinguishes observed facts vs. AI-generated findings vs. confirmed findings.
  - Computes SHA-256 provenance hashes and sanitizes clinical text inputs against prompt injection.

---

## 4. Service Layer & Workflow Orchestration
- `backend/app/services/imaging_service.py`:
  - Study ingestion, asset registration, order linkage.
  - Multimodal context assembly.
  - AI analysis execution & critical finding alert generation (creates `ClinicalAlert`).
  - Radiology report generation, editing, clinician sign-off / finalization, and amendment workflow.
  - RBAC checks and patient isolation enforcement.

---

## 5. REST API & FHIR R4 Interoperability
- `backend/app/api/v1/endpoints/imaging.py`:
  - `POST /patients/{patient_id}/imaging/studies`
  - `GET /patients/{patient_id}/imaging/studies`
  - `GET /imaging/studies/{study_id}`
  - `POST /imaging/studies/{study_id}/assets`
  - `GET /imaging/studies/{study_id}/assets`
  - `POST /imaging/studies/{study_id}/analyze`
  - `GET /imaging/studies/{study_id}/findings`
  - `POST /imaging/studies/{study_id}/report`
  - `GET /imaging/reports/{report_id}`
  - `POST /imaging/reports/{report_id}/submit-review`
  - `POST /imaging/reports/{report_id}/finalize`
  - `POST /imaging/reports/{report_id}/amend`
  - `GET /patients/{patient_id}/imaging/timeline`
- `backend/app/api/v1/endpoints/fhir.py`:
  - `GET /fhir/ImagingStudy/{study_id}`
  - `GET /fhir/DiagnosticReport/{report_id}`
  - `GET /fhir/ImagingObservation/{finding_id}`

---

## 6. Frontend Workspace
- `frontend/src/components/imaging/ImagingRadiologyWorkspace.tsx`:
  - Study timeline & modality filter.
  - DICOM/Image asset inspection.
  - AI findings list with confidence scores & critical finding banners.
  - Structured report editor & clinician signoff / amendment workflows.
  - FHIR export inspector.
- `DashboardPage.tsx`:
  - Add `🩻 Medical Imaging & Radiology` tab.

---

## 7. Verification Strategy
- **Backend Tests**: `backend/tests/test_medical_imaging.py`
- **Frontend Tests**: `frontend/src/test/imaging.test.tsx`
- **Full Backend Regression**: `pytest backend/tests -q`
- **Alembic Migration Verification**: `alembic upgrade head --sql`
- **Frontend Build**: `npm run build`
