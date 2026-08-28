# Longitudinal Clinical Timeline Documentation

## 1. Overview
The Longitudinal Clinical Timeline organizes a patient's historical medical records into a unified, chronologically ordered stream. Rather than requiring clinicians or patients to manually browse disconnected records, the timeline aggregates:
1. **Encounters**: Inpatient admissions, initial consultations, follow-ups, telehealth sessions, and emergency visits.
2. **Appointments**: Historical and upcoming visits with duration, consultation mode, and status.
3. **Medical Documents**: Uploaded clinical notes, discharge summaries, laboratory reports, and radiology scans.
4. **Clinical Entities**: Fine-grained diagnoses, prescribed medications, and laboratory findings extracted from text chunks.

---

## 2. Architecture & Data Flow

```
+-------------------------------------------------------------------------+
|                         PostgreSQL Primary Store                        |
|   (Encounters, Appointments, Medical Documents, Document Chunks)        |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                       Clinical Timeline Engine                          |
|  - Aggregates authoritative records                                     |
|  - Extracts granular facts from document chunks                         |
|  - Normalizes timestamps & attaches document/chunk citations            |
|  - Filters by date boundaries (start_date, end_date) & event_type       |
|  - Applies chronological sorting (asc / desc) and pagination           |
+-------------------------------------------------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+------------------------+                     +------------------------+
|  Timeline Event Stream |                     |  Longitudinal Summary  |
|  (JSON Event List)     |                     |  (RAG Grounded LLM)    |
+------------------------+                     +------------------------+
```

---

## 3. Data Schema

### `ClinicalTimelineEvent`
- `event_id`: Unique identifier (e.g. `EVT-20260828-A1B2C3D4`)
- `patient_id`: Target patient public ID
- `event_date`: ISO datetime of the clinical occurrence
- `event_type`: Event category (`encounter`, `appointment`, `document_upload`, `diagnosis`, `medication_prescribed`, `lab_result`, `procedure`, `clinical_event`)
- `title`: Short descriptive title
- `description`: Detailed clinical description
- `source_document_id`: Associated document ID (if applicable)
- `source_chunk_id`: Source text chunk ID (if applicable)
- `page_number`: Document page number (if applicable)
- `confidence`: Extraction certainty score (0.0 to 1.0)
- `citations`: Verified `RAGCitation` objects linking to underlying source chunks

---

## 4. API Endpoints

### 4.1 List Timeline Events
`GET /api/v1/patients/{patient_id}/timeline`

#### Query Parameters:
- `start_date` (optional): Filter events on or after ISO timestamp
- `end_date` (optional): Filter events on or before ISO timestamp
- `event_type` (optional): Filter by category
- `skip` (default 0): Pagination offset
- `limit` (default 50, max 200): Pagination limit
- `sort_order` (default `desc`): Sort order (`asc` or `desc`)

### 4.2 Longitudinal Timeline Summary
`GET /api/v1/patients/{patient_id}/timeline/summary`

Returns a narrative summary synthesized using patient-scoped RAG and verified citations.
