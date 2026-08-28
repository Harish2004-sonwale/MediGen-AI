# MediGen AI — Medical Records & Clinical Encounters

This document provides technical documentation for the **Medical Records & Clinical Encounters Module** in the MediGen AI Clinical Decision Support System.

---

## 1. Overview & Architectural Design

The Clinical Encounters module establishes the core clinical documentation repository in MediGen AI. Every encounter represents a clinician-authored consultation, progress note, emergency triage, or routine examination linked to a specific patient and attending healthcare provider.

```text
Entity Relationship Hierarchy:

┌─────────────────┐
│      User       │ (Attending Clinician / Healthcare User)
└────────┬────────┘
         │ 1
         │
         │ *
┌────────▼────────┐          1       * ┌──────────────────────────┐
│     Patient     ├───────────────────►│    Clinical Encounter    │
└─────────────────┘                    │     (Medical Record)     │
                                       └──────────────────────────┘
```

---

## 2. Preservation of Historical Clinical Records

> [!IMPORTANT]
> **Clinical History Preservation Principle**:
> Healthcare data governance mandates that clinical histories must never be deleted or destroyed when a patient account is deactivated or archived.
>
> 1. **No Hard Cascade Deletion**: The relationship `Patient → Encounter` does **not** use ORM cascade delete (`cascade="all, delete-orphan"` is intentionally omitted).
> 2. **Database Level Protection**: The foreign key `encounters.patient_id -> patients.id` enforces `ON DELETE RESTRICT` at the PostgreSQL engine level, preventing accidental hard deletion of patient records that contain clinical encounters.
> 3. **Soft Deactivation**: When a patient is deactivated (`DELETE /api/v1/patients/{patient_id}`), only their `status` is updated to `"inactive"`. All historical encounters remain intact, searchable, and fully accessible to authorized clinical personnel.

---

## 3. Database Schema (`encounters` Table)

Defined in [`app/models/encounter.py`](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/encounter.py) and managed via Alembic migration `0003_create_encounters_table.py`:

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal relational ID |
| `encounter_id` | `VARCHAR(32)` | `UNIQUE`, `NOT NULL`, `INDEX` | Safe public encounter identifier (`ENC-YYYYMMDD-XXXX`) |
| `patient_id` | `INTEGER` | `FOREIGN KEY (patients.id)`, `RESTRICT`, `NOT NULL`, `INDEX` | Relational reference to patient |
| `attending_user_id` | `INTEGER` | `FOREIGN KEY (users.id)`, `SET NULL`, `NULLABLE`, `INDEX` | Relational reference to clinician/user |
| `encounter_date` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, `INDEX`, Default: `now()` | Date and time of clinical encounter |
| `encounter_type` | `VARCHAR(50)` | `NOT NULL`, Default: `initial_consultation` | Classification (`initial_consultation`, `follow_up`, `emergency`, `routine_checkup`, `telehealth`) |
| `chief_complaint` | `VARCHAR(255)` | `NOT NULL` | Primary reason or clinical symptom for the visit |
| `clinical_notes` | `TEXT` | `NULLABLE` | Clinician physical examination notes, history of present illness |
| `assessment` | `TEXT` | `NULLABLE` | Clinician working diagnosis and diagnostic assessment |
| `plan` | `TEXT` | `NULLABLE` | Management plan, therapy recommendations, prescriptions, and follow-up |
| `status` | `VARCHAR(20)` | `NOT NULL`, `INDEX`, Default: `completed` | Workflow status (`in_progress`, `completed`, `amended`, `cancelled`) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Record creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Last modification timestamp |

---

## 4. Authorization Model & Future Evolution

### 4.1 Current Foundation (Role-Based Access Control)
In this milestone, centralized role-based authorization is enforced via FastAPI dependency injection:

| Role | Create Encounter | List / Search Encounters | View Encounter | Update Encounter |
|---|:---:|:---:|:---:|:---:|
| **`admin`** | ✅ | ✅ | ✅ | ✅ |
| **`doctor`** | ✅ | ✅ | ✅ | ✅ |
| **`healthcare_staff`** | ✅ | ✅ | ✅ | ✅ |
| **Unauthenticated / Anonymous** | ❌ (401) | ❌ (401) | ❌ (401) | ❌ (401) |

### 4.2 Planned Fine-Grained Authorization Roadmap
> [!NOTE]
> In production healthcare systems, broad role-based permissions are insufficient for strict privacy compliance.
> When **Doctor Management** and **Appointment/Scheduling** modules are implemented, MediGen AI will introduce:
> - **Doctor-Patient Care Team Assignments**: Only assigned clinicians or covering providers can view sensitive clinical progress notes.
> - **Encounter Author Verification**: Only the authoring clinician or clinical director can amend assessments and plans.
> - **Break-Glass Emergency Auditing**: Explicit auditable override access for emergency departments.

---

## 5. API Endpoints Reference

### 5.1 Record an Encounter
- **Endpoint**: `POST /api/v1/patients/{patient_id}/encounters`
- **Request Body**:
  ```json
  {
    "encounter_type": "initial_consultation",
    "chief_complaint": "Persistent productive cough and fever (38.5C) for 4 days",
    "clinical_notes": "Bilateral lung auscultation reveals mild expiratory wheeze on right base.",
    "assessment": "Community-acquired acute bronchitis.",
    "plan": "Oral hydration, rest, Salbutamol inhaler as needed. Re-evaluate if symptoms worsen.",
    "status": "completed"
  }
  ```
- **Response (`201 Created`)**:
  ```json
  {
    "id": 1,
    "encounter_id": "ENC-20260828-A1B2",
    "patient_id": "PAT-20260828-B7C9",
    "attending_user_id": 2,
    "attending_user_name": "Dr. Alice Smith",
    "encounter_date": "2026-08-28T16:05:00.000000Z",
    "encounter_type": "initial_consultation",
    "chief_complaint": "Persistent productive cough and fever (38.5C) for 4 days",
    "clinical_notes": "Bilateral lung auscultation reveals mild expiratory wheeze on right base.",
    "assessment": "Community-acquired acute bronchitis.",
    "plan": "Oral hydration, rest, Salbutamol inhaler as needed. Re-evaluate if symptoms worsen.",
    "status": "completed",
    "created_at": "2026-08-28T16:05:00.000000Z",
    "updated_at": "2026-08-28T16:05:00.000000Z"
  }
  ```

### 5.2 List Patient Encounters (Chronological & Paginated)
- **Endpoint**: `GET /api/v1/patients/{patient_id}/encounters?page=1&size=20&status=completed`
- **Response (`200 OK`)**: Paginated list of encounters ordered descending by encounter date.

### 5.3 Get Encounter Details
- **Endpoint**: `GET /api/v1/encounters/{encounter_id}`
- **Response (`200 OK`)**: Full encounter record with attending user information.

### 5.4 Update Encounter (PATCH)
- **Endpoint**: `PATCH /api/v1/encounters/{encounter_id}`
- **Request Body**:
  ```json
  {
    "plan": "Oral hydration, rest, Salbutamol inhaler + added Azithromycin 500mg daily for 3 days.",
    "status": "amended"
  }
  ```
- **Response (`200 OK`)**: Updated encounter record.

---

## 6. Medical Data Safety & Clinician Authorship

> [!IMPORTANT]
> **Clinician Authorship Principle**:
> All records in the `encounters` table represent human clinician-authored medical documentation.
> - MediGen AI strictly segregates human clinical records from future AI decision-support insights.
> - Future AI features will analyze these encounters as assistive context, but will **never** overwrite or replace human clinician assessment fields.

---

## 7. Migration Instructions

To apply the encounters migration to PostgreSQL:
```powershell
cd backend
alembic upgrade head
```
