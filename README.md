# MediGen AI - Clinical Decision Support System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/Auth-JWT%20%2B%20Bcrypt-orange.svg)](docs/authentication.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MediGen AI is an AI-powered Clinical Decision Support System (CDSS) designed to assist healthcare professionals with:
- Patient information management
- Doctor profile verification and discovery
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
- **Milestone 6 — Doctor Management Foundation**: Implemented & Verified ✅
  - [x] Doctor ORM model with 1-to-1 user association and unique registration number
  - [x] Doctor verification lifecycle (`pending`, `verified`, `rejected`, `inactive`)
  - [x] Multi-field patient discovery search (specialization, experience, location, mode)
  - [x] Doctor self-profile management (`GET/PATCH /api/v1/doctors/me`)
  - [x] Admin credential verification & rejection workflows
  - [x] Availability toggle (`available`, `busy`, `on_leave`, `unavailable`)
  - [x] Alembic migration (`0004_create_doctors_table.py`)
  - [x] Comprehensive automated test suite (40 unit tests, 2 live integration tests)
  - [x] Module documentation ([`docs/doctors.md`](docs/doctors.md))

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
│   │   │   └── 0004_create_doctors_table.py
│   │   └── env.py         # Migration environment configuration
│   ├── app/
│   │   ├── ai/            # AI pipelines & model integrations (planned)
│   │   ├── api/           # API routers & endpoints
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py       # Authentication endpoints
│   │   │   │   │   ├── doctors.py    # Doctor management endpoints
│   │   │   │   │   ├── encounters.py # Clinical encounter endpoints
│   │   │   │   │   └── patients.py   # Patient management endpoints
│   │   │   │   └── api.py            # API v1 router aggregator
│   │   │   └── deps.py    # Auth & role-checking dependencies
│   │   ├── core/          # Configuration & security
│   │   │   ├── config.py  # Pydantic Settings configuration
│   │   │   └── security.py# Password hashing & JWT helpers
│   │   ├── database/      # Database foundation
│   │   │   ├── base.py    # SQLAlchemy 2.0 DeclarativeBase
│   │   │   ├── connection.py # Engine & pool setup
│   │   │   └── session.py # Request-scoped session dependency
│   │   ├── models/        # Database ORM models (User, Patient, Encounter, Doctor)
│   │   ├── schemas/       # Pydantic schemas (User, Patient, Encounter, Doctor, Token)
│   │   ├── services/      # Business logic (user, patient, encounter, doctor services)
│   │   ├── __init__.py
│   │   └── main.py        # FastAPI entrypoint
│   ├── tests/             # Automated test suite
│   │   ├── conftest.py    # Pytest fixtures & in-memory test database
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
├── database/              # Database scripts and seeds (planned)
├── datasets/              # Clinical test datasets (planned)
├── docker/                # Container configurations (planned)
├── docs/                  # Architecture & system documentation
│   ├── authentication.md  # Auth & RBAC documentation
│   ├── database.md        # PostgreSQL database guide
│   ├── doctors.md         # Doctor management documentation
│   ├── medical_records.md # Clinical encounters documentation
│   └── patients.md        # Patient management documentation
├── frontend/              # Web application user interface (planned)
├── screenshots/           # UI captures & visual assets (planned)
├── tests/                 # Integration & end-to-end test suites (planned)
├── .gitignore             # Git ignore definitions
├── LICENSE                # MIT License
└── README.md              # Project documentation
```

---

## 🚀 Backend Setup & Local Development

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+ (installed locally)
- Git

### 1. Set Up Virtual Environment

From the project root:

```bash
cd backend
python -m venv .venv

# Activate the virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (CMD):
.venv\Scripts\activate.bat
# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Update `.env` with your local PostgreSQL credentials and a secure JWT secret key:

```env
DATABASE_URL="postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/medigen_ai"
JWT_SECRET_KEY="YOUR_ACTUAL_SECURE_JWT_SECRET_KEY"
```

### 4. Apply Database Migrations

```bash
alembic upgrade head
```

### 5. Start the FastAPI Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Root Endpoint:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Application Health:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Database Health:** [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db)
- **Auth Health:** [http://127.0.0.1:8000/api/v1/auth/health](http://127.0.0.1:8000/api/v1/auth/health)
- **Doctors API:** [http://127.0.0.1:8000/api/v1/doctors](http://127.0.0.1:8000/api/v1/doctors)
- **Patients API:** [http://127.0.0.1:8000/api/v1/patients](http://127.0.0.1:8000/api/v1/patients)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run the complete test suite with `pytest`:

```bash
# Run unit tests
pytest -v

# Run including live PostgreSQL integration tests (requires live database)
RUN_DB_INTEGRATION_TESTS=1 pytest -v
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
| `GET` | `/api/v1/doctors` | Authenticated | Search and discover doctors (verified only for non-admin) | `200 OK` |
| `GET` | `/api/v1/doctors/me` | Doctor / Admin | Retrieve own doctor profile | `200 OK` |
| `PATCH` | `/api/v1/doctors/me` | Doctor / Admin | Update own professional profile | `200 OK` |
| `GET` | `/api/v1/doctors/{doctor_id}` | Authenticated | Retrieve doctor profile (verified only for non-admin) | `200 OK` |
| `PATCH` | `/api/v1/doctors/{doctor_id}` | Admin / Doctor | Update doctor profile | `200 OK` |
| `DELETE` | `/api/v1/doctors/{doctor_id}` | Admin | Soft-deactivate doctor profile | `200 OK` |
| `POST` | `/api/v1/doctors/{doctor_id}/verify` | Admin | Verify doctor credentials and profile | `200 OK` |
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
| `PATCH` | `/api/v1/encounters/{encounter_id}` | Clinical Roles | Update encounter notes, assessment, plan, status | `200 OK` |
| `GET` | `/docs` | Public | OpenAPI / Swagger Documentation | `200 OK` |
| `GET` | `/redoc` | Public | ReDoc API Documentation | `200 OK` |

---

## 🗺️ Project Roadmap & Planned Milestones

1. **Milestone 1: Backend Foundation** *(Completed & Pushed)* ✅
2. **Milestone 2: Database Layer & Relational Modeling** *(Completed & Pushed)* ✅
3. **Milestone 3: Authentication & Role-Based Access Control** *(Completed & Pushed)* ✅
4. **Milestone 4: Patient Management** *(Completed & Pushed)* ✅
5. **Milestone 5: Medical Records & Clinical Encounters** *(Completed & Pushed)* ✅
6. **Milestone 6: Doctor Management Foundation** *(Implemented & Ready for Review)* ✅
7. **Milestone 7: Appointment Scheduling & Care Team Allocation** *(Planned)*
8. **Milestone 8: Clinical Retrieval-Augmented Generation (RAG) & Document Analysis** *(Planned)*
9. **Milestone 9: Clinical Frontend Dashboard** *(Planned)*
10. **Milestone 10: End-to-End Testing, Security Audits, and Production Deployment** *(Planned)*
