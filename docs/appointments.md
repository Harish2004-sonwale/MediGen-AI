# MediGen AI — Appointment Scheduling & Care Team Allocation Module

This document provides technical documentation for the **Appointment Scheduling Module** in the MediGen AI Clinical Decision Support System.

---

## 1. Architecture & Entity Relationships

The Appointment module connects patients with verified medical providers, managing scheduling, conflict prevention, status lifecycles, and role-based permissions.

```text
Entity Relationship Hierarchy:

┌─────────────────┐             ┌─────────────────┐
│     Patient     │             │     Doctor      │
└────────┬────────┘             └────────┬────────┘
         │ 1                             │ 1
         │                               │
         │ *                           * │
┌────────▼───────────────────────────────▼────────┐
│                  Appointment                    │
│   (patient_id, doctor_id, date, status, mode)   │
└─────────────────────────────────────────────────┘
```

---

## 2. Database Schema

Defined in [`app/models/appointment.py`](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/appointment.py) and created via Alembic migration `0006_create_appointments_table.py`:

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal relational database ID |
| `appointment_id` | `VARCHAR(32)` | `UNIQUE`, `NOT NULL`, `INDEX` | Public safe appointment identifier (`APT-YYYYMMDD-XXXX`) |
| `patient_id` | `INTEGER` | `FOREIGN KEY (patients.id)`, `RESTRICT`, `NOT NULL`, `INDEX` | Patient receiving consultation |
| `doctor_id` | `INTEGER` | `FOREIGN KEY (doctors.id)`, `RESTRICT`, `NOT NULL`, `INDEX` | Attending medical provider |
| `appointment_date` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, `INDEX` | Scheduled consultation date and time |
| `duration_minutes` | `INTEGER` | `NOT NULL`, Default: `30` | Expected appointment duration (10–240 mins) |
| `consultation_mode` | `VARCHAR(50)` | `NOT NULL`, Default: `in_person` | Format (`in_person`, `telehealth`, `both`) |
| `reason_for_visit` | `VARCHAR(255)` | `NOT NULL` | Chief symptom or primary reason for booking |
| `status` | `VARCHAR(20)` | `NOT NULL`, `INDEX`, Default: `scheduled` | Lifecycle state (`scheduled`, `confirmed`, `completed`, `cancelled`, `rejected`) |
| `notes` | `TEXT` | `NULLABLE` | Preparation instructions or clinical notes |
| `cancellation_reason` | `TEXT` | `NULLABLE` | Documented reason if appointment was cancelled |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Record creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Last update timestamp |

---

## 3. Status Lifecycle

Appointments follow an explicit clinical lifecycle:

```text
       ┌───────────────┐
       │   Scheduled   │ (Created by patient/staff/admin)
       └───────┬───────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌──────────────┐┌──────────────┐
│  Confirmed   ││  Cancelled   │ (Cancelled with documented reason)
└──────┬───────┘└──────────────┘
       │
       ▼
┌──────────────┐
│  Completed   │ (Marked complete post-consultation)
└──────────────┘
```

1. **`scheduled`**: Initial status upon successful booking.
2. **`confirmed`**: Verified by clinic staff or the attending doctor (`POST /api/v1/appointments/{id}/confirm`).
3. **`completed`**: Clinical consultation concluded (`POST /api/v1/appointments/{id}/complete`).
4. **`cancelled`**: Appointment cancelled (`POST /api/v1/appointments/{id}/cancel`) with documented justification.

---

## 4. Scheduling & Conflict Rules

Before an appointment is scheduled:
- **Patient Verification**: Patient must exist and have `status = active`.
- **Doctor Verification**: Doctor must exist, have `verification_status = verified`, and not be inactive.
- **Future Time Window**: Appointment datetime must be strictly in the future (`appointment_date > now`).
- **Slot Conflict Prevention**: Checks that the doctor does not have any active appointment (`scheduled` or `confirmed`) whose time window `[appointment_date, appointment_date + duration]` overlaps with the requested slot.

---

## 5. API Endpoints Reference

| Method | Endpoint | Access Level | Description |
|---|---|---|---|
| `POST` | `/api/v1/appointments` | Authenticated | Schedule a new appointment with slot conflict checks |
| `GET` | `/api/v1/appointments` | Authenticated | List appointments (Patients see own, Doctors see assigned, Admin/Staff see all) |
| `GET` | `/api/v1/appointments/{appointment_id}` | Authenticated | View appointment details |
| `PATCH` | `/api/v1/appointments/{appointment_id}` | Admin / Staff / Doctor | Update appointment details or reschedule |
| `POST` | `/api/v1/appointments/{appointment_id}/confirm` | Admin / Staff / Doctor | Confirm scheduled appointment |
| `POST` | `/api/v1/appointments/{appointment_id}/cancel` | Admin / Staff / Doctor / Patient | Cancel appointment with reason |
| `POST` | `/api/v1/appointments/{appointment_id}/complete` | Admin / Staff / Doctor | Mark appointment completed |

---

## 6. Authorization Matrix

| Role | Book Appointment | View Own / Assigned | View Other | Confirm | Cancel Own | Cancel Other | Complete |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`admin`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`healthcare_staff`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`doctor`** | ✅ | ✅ (Assigned) | ❌ (403) | ✅ (Assigned) | ✅ (Assigned) | ❌ (403) | ✅ (Assigned) |
| **`patient`** | ✅ | ✅ (Own) | ❌ (403) | ❌ (403) | ✅ (Own) | ❌ (403) | ❌ (403) |
| **Unauthenticated** | ❌ (401) | ❌ (401) | ❌ (401) | ❌ (401) | ❌ (401) | ❌ (401) | ❌ (401) |
