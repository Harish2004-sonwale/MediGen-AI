# MediGen AI — Patient Management Module

This document provides technical documentation for the **Patient Management Module** of the MediGen AI Clinical Decision Support System.

---

## 1. Overview & Architectural Design

The Patient Management module provides a secure, structured repository for patient demographics, contact records, and identification. It forms the core entity layer upon which future clinical encounters, medical documents, and AI decision-support insights will be anchored.

```text
Request Flow for Patient Management:

  Client Request (e.g. POST /api/v1/patients)
        │
        ▼ (Authorization: Bearer <JWT>)
  FastAPI Dependency (get_current_active_user & require_role)
        │
        ▼ (Pydantic Validation: PatientCreate / PatientUpdate)
  API Route Controller (app/api/v1/endpoints/patients.py)
        │
        ▼ (Business Logic & Patient ID Generation)
  Service Layer (app/services/patient_service.py)
        │
        ▼ (SQLAlchemy 2.0 ORM Mappings)
  PostgreSQL Database (patients table)
```

---

## 2. Patient Data Model & Schema

Defined in [`app/models/patient.py`](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/patient.py) and managed via Alembic migration `0002_create_patients_table.py`:

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal relational database ID |
| `patient_id` | `VARCHAR(32)` | `UNIQUE`, `NOT NULL`, `INDEX` | Safe public patient identifier (e.g., `PAT-20260828-A4F2`) |
| `first_name` | `VARCHAR(100)` | `NOT NULL`, `INDEX` | Patient first legal name |
| `last_name` | `VARCHAR(100)` | `NOT NULL`, `INDEX` | Patient last legal name |
| `date_of_birth` | `DATE` | `NOT NULL` | Date of birth (YYYY-MM-DD) |
| `gender` | `VARCHAR(20)` | `NOT NULL` | Gender (`male`, `female`, `other`, `prefer_not_to_say`) |
| `phone` | `VARCHAR(30)` | `NULLABLE`, `INDEX` | Primary phone contact |
| `email` | `VARCHAR(255)` | `NULLABLE` | Patient email address |
| `address` | `VARCHAR(255)` | `NULLABLE` | Residential address |
| `emergency_contact_name` | `VARCHAR(100)` | `NULLABLE` | Emergency contact full name |
| `emergency_contact_phone` | `VARCHAR(30)` | `NULLABLE` | Emergency contact telephone number |
| `status` | `VARCHAR(20)` | `NOT NULL`, `INDEX`, Default: `active` | Patient status (`active`, `inactive`, `archived`) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Record creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Last modification timestamp |

---

## 3. Role-Based Permissions Matrix

| Endpoint | Method | Allowed Roles | Description |
|---|---|---|---|
| `/api/v1/patients` | `POST` | `admin`, `doctor`, `healthcare_staff` | Register new patient record |
| `/api/v1/patients` | `GET` | `admin`, `doctor`, `healthcare_staff` | Search and list patients with pagination |
| `/api/v1/patients/{patient_id}` | `GET` | `admin`, `doctor`, `healthcare_staff` | Retrieve full patient profile |
| `/api/v1/patients/{patient_id}` | `PATCH` | `admin`, `doctor`, `healthcare_staff` | Update patient demographics |
| `/api/v1/patients/{patient_id}` | `DELETE` | `admin`, `doctor` | Soft-delete / deactivate patient record |

---

## 4. API Endpoints Reference

### 4.1 Register a Patient
- **Endpoint**: `POST /api/v1/patients`
- **Request Body**:
  ```json
  {
    "first_name": "Eleanor",
    "last_name": "Vance",
    "date_of_birth": "1991-04-12",
    "gender": "female",
    "phone": "+1-555-0144",
    "email": "eleanor.vance@example.com",
    "address": "456 Hilltop Road, Boston, MA",
    "emergency_contact_name": "Thomas Vance",
    "emergency_contact_phone": "+1-555-0145"
  }
  ```
- **Response (`201 Created`)**:
  ```json
  {
    "id": 1,
    "patient_id": "PAT-20260828-B7C9",
    "first_name": "Eleanor",
    "last_name": "Vance",
    "date_of_birth": "1991-04-12",
    "gender": "female",
    "phone": "+1-555-0144",
    "email": "eleanor.vance@example.com",
    "address": "456 Hilltop Road, Boston, MA",
    "emergency_contact_name": "Thomas Vance",
    "emergency_contact_phone": "+1-555-0145",
    "status": "active",
    "created_at": "2026-08-28T15:50:00.000000Z",
    "updated_at": "2026-08-28T15:50:00.000000Z"
  }
  ```

### 4.2 List and Search Patients (Paginated)
- **Endpoint**: `GET /api/v1/patients?page=1&size=20&search=Eleanor&status=active`
- **Query Parameters**:
  - `page` (integer, default `1`): Current page.
  - `size` (integer, default `20`, max `100`): Results per page.
  - `search` (string, optional): Matches across `first_name`, `last_name`, `patient_id`, `phone`, and `email`.
  - `status` (string, optional): Filter by `active`, `inactive`, `archived`.
- **Response (`200 OK`)**:
  ```json
  {
    "items": [
      {
        "id": 1,
        "patient_id": "PAT-20260828-B7C9",
        "first_name": "Eleanor",
        "last_name": "Vance",
        "date_of_birth": "1991-04-12",
        "gender": "female",
        "phone": "+1-555-0144",
        "email": "eleanor.vance@example.com",
        "status": "active",
        "created_at": "2026-08-28T15:50:00.000000Z",
        "updated_at": "2026-08-28T15:50:00.000000Z"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 20,
    "total_pages": 1
  }
  ```

### 4.3 Get Patient by Identifier
- **Endpoint**: `GET /api/v1/patients/{patient_id}`
- **Response (`200 OK`)**: Full patient object. Returns `404 Not Found` if identifier does not match.

### 4.4 Update Patient (PATCH)
- **Endpoint**: `PATCH /api/v1/patients/{patient_id}`
- **Request Body**:
  ```json
  {
    "phone": "+1-555-9988",
    "address": "789 New Meadow Lane, Boston, MA"
  }
  ```
- **Response (`200 OK`)**: Updated patient record. Immutable fields (`id`, `patient_id`, `created_at`) are protected from modification.

### 4.5 Deactivate Patient (Soft-Delete)
- **Endpoint**: `DELETE /api/v1/patients/{patient_id}`
- **Response (`200 OK`)**:
  ```json
  {
    "id": 1,
    "patient_id": "PAT-20260828-B7C9",
    "status": "inactive",
    ...
  }
  ```

---

## 5. Deactivation / Soft-Delete Strategy

In healthcare systems, hard deleting clinical patient records introduces compliance and audit hazards. MediGen AI implements **soft deactivation**:
- Calling `DELETE /api/v1/patients/{patient_id}` transitions `status` to `inactive`.
- The record remains retained in the database for auditing and continuity of care.
- Reactivation can be performed anytime via `PATCH /api/v1/patients/{patient_id}` with `{"status": "active"}`.

---

## 6. Migration Instructions

To apply the patient schema to PostgreSQL:
```powershell
cd backend
alembic upgrade head
```
