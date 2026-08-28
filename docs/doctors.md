# MediGen AI — Doctor Management & Discovery Module

This document provides technical documentation for the **Doctor Management & Directory Discovery Module** in the MediGen AI Clinical Decision Support System.

---

## 1. Overview & Architecture

The Doctor Management module maintains verified medical provider profiles, credentials, department affiliations, specializations, and real-time consultation availability. It allows patients to search and filter doctors across clinical departments, while providing administrators with rigorous credential verification workflows.

```text
Entity Relationship Hierarchy:

┌─────────────────┐
│      User       │ (Authentication: Email / Password Hash / Role)
└────────┬────────┘
         │ 1
         │ (1-to-1 Association via user_id)
         │ 1
┌────────▼────────┐          1       * ┌──────────────────────────┐
│     Doctor      ├───────────────────►│       Appointments       │
│    Profile      │                    │     (Future Milestone)   │
└────────┬────────┘                    └──────────────────────────┘
         │ 1
         │ *
┌────────▼────────┐
│    Clinical     │
│   Encounters    │ (Attending Provider Historical Records)
└─────────────────┘
```

---

## 2. Doctor Data Model & Database Schema

Defined in [`app/models/doctor.py`](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/doctor.py) and managed via Alembic migrations `0004_create_doctors_table.py` and `0005_add_doctor_department.py`:

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal database primary key |
| `doctor_id` | `VARCHAR(32)` | `UNIQUE`, `NOT NULL`, `INDEX` | Safe public doctor identifier (`DOC-YYYYMMDD-XXXX`) |
| `user_id` | `INTEGER` | `FOREIGN KEY (users.id)`, `UNIQUE`, `RESTRICT`, `NOT NULL`, `INDEX` | Relational 1-to-1 link to user authentication account |
| `full_name` | `VARCHAR(100)` | `NOT NULL`, `INDEX` | Full professional name |
| `professional_title` | `VARCHAR(50)` | `NOT NULL`, Default: `Dr.` | Professional prefix (e.g., `Dr.`, `MD`, `Prof. Dr.`) |
| `department` | `VARCHAR(100)` | `NOT NULL`, `INDEX`, Default: `General Medicine` | Clinical department (e.g., `Dentistry`, `Cardiology`, `Dermatology`, `Neurology`, `Pediatrics`) |
| `specialization` | `VARCHAR(100)` | `NOT NULL`, `INDEX` | Medical sub-specialization (e.g., `Orthodontist`, `Interventional Cardiology`) |
| `qualifications` | `VARCHAR(255)` | `NULLABLE` | Degrees and certifications (e.g., `MBBS, MD, BDS, MDS`) |
| `medical_degree` | `VARCHAR(100)` | `NULLABLE` | Primary medical degree |
| `medical_registration_number` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL`, `INDEX` | Official medical license registration number |
| `years_of_experience` | `INTEGER` | `NOT NULL`, Default: `0` | Years of clinical practice |
| `email` | `VARCHAR(255)` | `NOT NULL` | Professional email (synced with user account) |
| `phone` | `VARCHAR(30)` | `NULLABLE` | Clinical contact telephone number |
| `clinic_hospital_name` | `VARCHAR(150)` | `NULLABLE` | Primary hospital or clinic facility |
| `consultation_location` | `VARCHAR(255)` | `NULLABLE` | Room number or consultation facility address |
| `consultation_mode` | `VARCHAR(50)` | `NOT NULL`, Default: `in_person` | Mode (`in_person`, `telehealth`, `both`) |
| `professional_bio` | `TEXT` | `NULLABLE` | Clinical bio and areas of expertise |
| `profile_image_url` | `VARCHAR(500)` | `NULLABLE` | Public portrait URL |
| `verification_status` | `VARCHAR(20)` | `NOT NULL`, `INDEX`, Default: `pending` | State (`pending`, `verified`, `rejected`, `inactive`) |
| `availability_status` | `VARCHAR(20)` | `NOT NULL`, `INDEX`, Default: `available` | Availability (`available`, `busy`, `on_leave`, `unavailable`) |
| `rejection_reason` | `TEXT` | `NULLABLE` | Reason documented if verification is rejected |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Record creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Last modification timestamp |

---

## 3. Doctor Verification Workflow

Doctor profiles adhere to a strict verification lifecycle to protect clinical authenticity:

```text
       ┌───────────────┐
       │   Registered  │ (Admin or Doctor creates profile)
       └───────┬───────┘
               │
               ▼
       ┌───────────────┐
       │    Pending    │ (Unverified, hidden from patient discovery)
       └───────┬───────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌──────────────┐┌──────────────┐
│   Verified   ││   Rejected   │ (Rejection reason recorded, hidden from public)
└──────┬───────┘└──────────────┘
       │
       ▼
┌──────────────┐
│   Inactive   │ (Soft-deactivated by Admin, preserves historical consultations)
└──────────────┘
```

1. **Pending**: Initial state upon doctor profile creation. Hidden from patient directory searches.
2. **Verified**: Admin approves doctor credentials (`POST /api/v1/doctors/{doctor_id}/verify`). Doctor is indexed and made discoverable to patients.
3. **Rejected**: Admin rejects registration (`POST /api/v1/doctors/{doctor_id}/reject`) with required justification notes.
4. **Inactive**: Admin deactivates profile (`DELETE /api/v1/doctors/{doctor_id}`). Doctor is hidden from public discovery while preserving historical encounters and medical audit integrity.

---

## 4. Multi-Filter Directory Discovery & Search

The `GET /api/v1/doctors` endpoint supports combinable, case-insensitive query parameters connected with `AND` logic:

| Query Parameter | Type | Description | Example |
|---|---|---|---|
| `department` | `string` | Filter by department name | `department=Dentistry` |
| `specialization` | `string` | Filter by medical sub-specialty | `specialization=Orthodontist` |
| `search` | `string` | Multi-field search across doctor name, department, specialization, clinic | `search=Rahul` |
| `availability` / `availability_status` | `string` | Filter by availability status (`available`, `busy`, `on_leave`, `unavailable`) | `availability=available` |
| `min_experience` | `integer` | Minimum years of clinical practice | `min_experience=5` |
| `max_experience` | `integer` | Maximum years of clinical practice | `max_experience=20` |
| `location` | `string` | Filter by city, hospital, or clinic location | `location=Boston` |
| `consultation_mode` | `string` | Consultation mode (`in_person`, `telehealth`, `both`) | `consultation_mode=telehealth` |
| `page` | `integer` | Current page number (default: `1`) | `page=1` |
| `page_size` / `size` | `integer` | Results per page (default: `20`, max: `100`) | `page_size=10` |

### Multi-Filter Query Examples

```http
# Filter by clinical department
GET /api/v1/doctors?department=Dentistry

# Combined department + specialization
GET /api/v1/doctors?department=Dentistry&specialization=Orthodontist

# Combined department + availability
GET /api/v1/doctors?department=Dentistry&availability=available

# Keyword search
GET /api/v1/doctors?search=Rahul

# Department + minimum experience
GET /api/v1/doctors?department=Dentistry&min_experience=5

# Full multi-filter search
GET /api/v1/doctors?department=Dentistry&specialization=Orthodontist&availability=available&min_experience=5
```

---

## 5. Role-Based Permissions Matrix

| Endpoint | Method | Admin | Doctor (Self) | Doctor (Other) | Patient / Staff | Description |
|---|---|:---:|:---:|:---:|:---:|---|
| `/api/v1/doctors` | `POST` | ✅ | ✅ | ❌ | ❌ | Register new doctor profile |
| `/api/v1/doctors` | `GET` | ✅ (All) | ✅ (Public) | ✅ (Public) | ✅ (Verified only) | Filter & search doctor directory |
| `/api/v1/doctors/me` | `GET` | ✅ | ✅ | ❌ | ❌ | View authenticated doctor's full profile |
| `/api/v1/doctors/me` | `PATCH` | ✅ | ✅ | ❌ | ❌ | Update own professional profile |
| `/api/v1/doctors/{doctor_id}` | `GET` | ✅ (Full) | ✅ (Full) | ✅ (Public) | ✅ (Verified public only) | Retrieve doctor details |
| `/api/v1/doctors/{doctor_id}` | `PATCH` | ✅ (All fields) | ✅ (Own info) | ❌ | ❌ | Update doctor profile |
| `/api/v1/doctors/{doctor_id}` | `DELETE` | ✅ | ❌ | ❌ | ❌ | Soft deactivate doctor profile |
| `/api/v1/doctors/{doctor_id}/verify` | `POST` | ✅ | ❌ | ❌ | ❌ | Approve and verify doctor credentials |
| `/api/v1/doctors/{doctor_id}/reject` | `POST` | ✅ | ❌ | ❌ | ❌ | Reject doctor application |
| `/api/v1/doctors/{doctor_id}/activate` | `POST` | ✅ | ✅ (Own) | ❌ | ❌ | Set availability status to available |
| `/api/v1/doctors/{doctor_id}/deactivate`| `POST` | ✅ | ✅ (Own) | ❌ | ❌ | Set availability status to unavailable |

---

## 6. Migration Instructions

To apply all migrations including the doctor department column to PostgreSQL:
```powershell
cd backend
alembic upgrade head
```
