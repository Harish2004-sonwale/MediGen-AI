# MediGen AI - Clinical Decision Support System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/Auth-JWT%20%2B%20Bcrypt-orange.svg)](docs/authentication.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MediGen AI is an AI-powered Clinical Decision Support System (CDSS) designed to assist healthcare professionals with:
- Patient information management
- Doctor profile verification and department discovery
- Clinical appointment scheduling and conflict prevention
- Medical document analysis
- Clinical knowledge retrieval
- AI-assisted documentation
- Decision-support insights

---

## ⚕️ Healthcare Safety & Assistive Disclaimer

> [!IMPORTANT]
> **MediGen AI is designed strictly as an assistive clinical decision support tool.**
> All AI-generated outputs, analyses, summaries, and suggestions must undergo rigorous review and verification by certified healthcare professionals before any clinical application or treatment decision. MediGen AI does not provide standalone diagnostic determinations or replace professional medical judgment. Clinician-authored medical records remain strictly distinguishable and segregated from AI-generated assistance.

---

## 📌 Current Development Status

- **Milestone 1 — Initial Backend Foundation**: Completed & Pushed ✅
- **Milestone 2 — PostgreSQL Database Foundation**: Completed & Pushed ✅
- **Milestone 3 — Authentication & User Roles**: Completed & Pushed ✅
- **Milestone 4 — Patient Management**: Completed & Pushed ✅
- **Milestone 5 — Medical Records & Clinical Encounters**: Completed & Pushed ✅
- **Milestone 6 — Doctor Management & Department Discovery**: Implemented & Verified ✅
- **Milestone 7 — Appointment Scheduling & Care Team Allocation**: Implemented & Verified ✅
  - [x] Appointment ORM model with foreign keys to Patient & Doctor (`ondelete="RESTRICT"`)
  - [x] Appointment status lifecycle (`scheduled`, `confirmed`, `completed`, `cancelled`, `rejected`)
  - [x] Conflict prevention (validates future time & prevents overlapping doctor bookings)
  - [x] Role-based permissions (patients view own, doctors view assigned, admin/staff manage all)
  - [x] Alembic migration (`0006_create_appointments_table.py`)
  - [x] Comprehensive automated test suite (46 unit tests, 2 live integration tests)
  - [x] Module documentation ([`docs/appointments.md`](docs/appointments.md))

---

## 🛠️ Technology Stack

- **Language:** Python 3.11+
- **API Framework:** FastAPI (>=0.110.0)
- **ASGI Server:** Uvicorn (>=0.28.0)
- **ORM & Database:** SQLAlchemy 2.0 (>=2.0.28), Psycopg 3 (>=3.1.18), PostgreSQL (14+)
- **Migrations:** Alembic (>=1.13.0)
- **Security & Auth:** PyJWT (>=2.8.0), Bcrypt (>=4.0.1), Email-Validator (>=2.1.0)
- **Settings & Validation:** Pydantic (>=2.6.0), Pydantic Settings (>=2.2.0)
- **Testing & Client:** Pytest (>=8.0.0), HTTPX (>=0.27.0)

---

## 📁 Repository Structure

```text
MediGen-AI/
├── backend/
│   ├── alembic/           # Alembic database migrations
│   │   ├── versions/      # Migration scripts
│   │   │   ├── 0001_create_users_table.py
│   │   │   ├── 0002_create_patients_table.py
│   │   │   ├── 0003_create_encounters_table.py
│   │   │   ├── 0004_create_doctors_table.py
│   │   │   ├── 0005_add_doctor_department.py
│   │   │   └── 0006_create_appointments_table.py
│   │   └── env.py         # Migration environment configuration
│   ├── app/
│   │   ├── ai/            # AI pipelines & model integrations (planned)
│   │   ├── api/           # API routers & endpoints
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── appointments.py # Appointment scheduling endpoints
│   │   │   │   │   ├── auth.py         # Authentication endpoints
│   │   │   │   │   ├── doctors.py      # Doctor management endpoints
│   │   │   │   │   ├── encounters.py   # Clinical encounter endpoints
│   │   │   │   │   └── patients.py     # Patient management endpoints
│   │   │   │   └── api.py              # API v1 router aggregator
│   │   │   └── deps.py    # Auth & role-checking dependencies
│   │   ├── core/          # Configuration & security
│   │   │   ├── config.py  # Pydantic Settings configuration
│   │   │   └── security.py# Password hashing & JWT helpers
│   │   ├── database/      # Database foundation
│   │   │   ├── base.py    # SQLAlchemy 2.0 DeclarativeBase
│   │   │   ├── connection.py # Engine & pool setup
│   │   │   └── session.py # Request-scoped session dependency
│   │   ├── models/        # Database ORM models (User, Patient, Encounter, Doctor, Appointment)
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic services
│   │   ├── __init__.py
│   │   └── main.py        # FastAPI entrypoint
│   ├── tests/             # Automated test suite
│   │   ├── conftest.py    # Pytest fixtures & in-memory test database
│   │   ├── test_appointments.py # Appointment scheduling & conflict tests
│   │   ├── test_auth.py   # Auth, JWT, and RBAC tests
│   │   ├── test_doctors.py# Doctor profile, verification, and discovery tests
│   │   ├── test_encounters.py # Clinical encounter tests
│   │   ├── test_patients.py # Patient management tests
│   │   ├── test_database_health.py      # DB health tests
│   │   ├── test_database_integration.py # Live PostgreSQL integration tests
│   │   └── test_main.py   # Root & app health tests
│   ├── .env.example       # Environment configuration template
│   ├── alembic.ini        # Alembic configuration
│   ├── pytest.ini         # Pytest configuration
│   └── requirements.txt   # Backend dependencies
├── docs/                  # Architecture & system documentation
│   ├── appointments.md    # Appointment scheduling documentation
│   ├── authentication.md  # Auth & RBAC documentation
│   ├── database.md        # PostgreSQL database guide
│   ├── doctors.md         # Doctor management documentation
│   ├── medical_records.md # Clinical encounters documentation
│   └── patients.md        # Patient management documentation
├── LICENSE                # MIT License
└── README.md              # Project documentation
```

---

## 📡 API Endpoints

| Method | Endpoint | Access | Description | Status Code |
|---|---|---|---|---|
| `GET` | `/` | Public | API Root / Welcome | `200 OK` |
| `GET` | `/health` | Public | Application Health Check | `200 OK` |
| `GET` | `/health/db` | Public | PostgreSQL Database Connectivity Check | `200 OK` / `503 Unavailable` |
| `POST` | `/api/v1/auth/register` | Public | Register new user | `201 Created` |
| `POST` | `/api/v1/auth/login` | Public | Login and obtain JWT Bearer Token | `200 OK` |
| `GET` | `/api/v1/auth/me` | Authenticated | Get current user profile | `200 OK` |
| `GET` | `/api/v1/auth/health` | Public | Auth Module Health Check | `200 OK` |
| `POST` | `/api/v1/doctors` | Admin / Doctor | Register doctor profile | `201 Created` |
| `GET` | `/api/v1/doctors` | Authenticated | Search and discover doctors across departments | `200 OK` |
| `GET` | `/api/v1/doctors/me` | Doctor / Admin | Retrieve own doctor profile | `200 OK` |
| `PATCH` | `/api/v1/doctors/me` | Doctor / Admin | Update own professional profile | `200 OK` |
| `GET` | `/api/v1/doctors/{doctor_id}` | Authenticated | Retrieve doctor profile | `200 OK` |
| `PATCH` | `/api/v1/doctors/{doctor_id}` | Admin / Doctor | Update doctor profile | `200 OK` |
| `DELETE` | `/api/v1/doctors/{doctor_id}` | Admin | Soft-deactivate doctor profile | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/verify` | Admin | Verify doctor credentials | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/reject` | Admin | Reject doctor verification application | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/activate` | Admin / Doctor | Set doctor availability to available | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/deactivate`| Admin / Doctor | Set doctor availability to unavailable | `200 OK` |
| `POST` | `/api/v1/patients` | Clinical Roles | Register new patient record | `201 Created` |
| `GET` | `/api/v1/patients` | Clinical Roles | Search and list patients (paginated) | `200 OK` |
| `GET` | `/api/v1/patients/{patient_id}` | Clinical Roles | Retrieve patient profile by patient_id | `200 OK` |
| `PATCH` | `/api/v1/patients/{patient_id}` | Clinical Roles | Update patient demographic details | `200 OK` |
| `DELETE` | `/api/v1/patients/{patient_id}` | Admin / Doctor | Soft-delete / deactivate patient record | `200 OK` |
| `POST` | `/api/v1/patients/{patient_id}/encounters` | Clinical Roles | Record a new clinical encounter for patient | `201 Created` |
| `GET` | `/api/v1/patients/{patient_id}/encounters` | Clinical Roles | List chronological encounters for patient | `200 OK` |
| `GET` | `/api/v1/encounters/{encounter_id}` | Clinical Roles | Retrieve encounter details by encounter identifier | `200 OK` |
| `PATCH` | `/api/v1/encounters/{encounter_id}` | Clinical Roles | Update encounter notes, assessment, plan | `200 OK` |
| `POST` | `/api/v1/appointments` | Authenticated | Schedule a new appointment | `201 Created` |
| `GET` | `/api/v1/appointments` | Authenticated | List and filter appointments | `200 OK` |
| `GET` | `/api/v1/appointments/{appointment_id}` | Authenticated | Get appointment details | `200 OK` |
| `PATCH` | `/api/v1/appointments/{appointment_id}` | Admin / Staff / Doctor | Reschedule / update appointment | `200 OK` |
| `POST` | `/api/v1/appointments/{appointment_id}/confirm` | Admin / Staff / Doctor | Confirm scheduled appointment | `200 OK` |
| `POST` | `/api/v1/appointments/{appointment_id}/cancel` | Authenticated | Cancel scheduled appointment | `200 OK` |
| `POST` | `/api/v1/appointments/{appointment_id}/complete` | Admin / Staff / Doctor | Mark appointment completed | `200 OK` |
| `GET` | `/docs` | Public | OpenAPI / Swagger Documentation | `200 OK` |
| `GET` | `/redoc` | Public | ReDoc API Documentation | `200 OK` |

---

## 🗺️ Project Roadmap & Planned Milestones

1. **Milestone 1: Backend Foundation** *(Completed & Pushed)* ✅
2. **Milestone 2: Database Layer & Relational Modeling** *(Completed & Pushed)* ✅
3. **Milestone 3: Authentication & Role-Based Access Control** *(Completed & Pushed)* ✅
4. **Milestone 4: Patient Management** *(Completed & Pushed)* ✅
5. **Milestone 5: Medical Records & Clinical Encounters** *(Completed & Pushed)* ✅
6. **Milestone 6: Doctor Management & Department Discovery** *(Implemented & Verified)* ✅
7. **Milestone 7: Appointment Scheduling & Care Team Allocation** *(Implemented & Verified)* ✅
8. **Milestone 8: Clinical Retrieval-Augmented Generation (RAG) & Document Analysis** *(Planned)*
9. **Milestone 9: Clinical Frontend Dashboard** *(Planned)*
10. **Milestone 10: End-to-End Testing, Security Audits, and Production Deployment** *(Planned)*
