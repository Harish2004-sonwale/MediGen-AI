# MediGen AI - Clinical Decision Support System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MediGen AI is an AI-powered Clinical Decision Support System (CDSS) designed to assist healthcare professionals with:
- Patient information management
- Medical document analysis
- Clinical knowledge retrieval
- AI-assisted documentation
- Decision-support insights

---

## ⚕️ Healthcare Safety & Assistive Disclaimer

> [!IMPORTANT]
> **MediGen AI is designed strictly as an assistive clinical decision support tool.**
> All AI-generated outputs, analyses, summaries, and suggestions must undergo rigorous review and verification by certified healthcare professionals before any clinical application or treatment decision. MediGen AI does not provide standalone diagnostic determinations or replace professional medical judgment.

---

## 📌 Current Development Status

- **Milestone 1 — Initial Backend Foundation**: Completed & Pushed ✅
- **Milestone 2 — PostgreSQL Database Foundation**: Implemented & Verified ✅
  - [x] Modern SQLAlchemy 2.0 ORM base and Psycopg 3 driver configured
  - [x] Connection pooling with liveness verification (`pool_pre_ping=True`)
  - [x] Request-scoped session management (`get_db` FastAPI dependency)
  - [x] Database health check endpoint (`GET /health/db`) with safe error handling
  - [x] Unit test suite and live integration test configuration
  - [x] Comprehensive database setup documentation ([`docs/database.md`](docs/database.md))

---

## 🛠️ Technology Stack

- **Language:** Python 3.11+
- **API Framework:** FastAPI (>=0.110.0)
- **ASGI Server:** Uvicorn (>=0.28.0)
- **ORM & Database:** SQLAlchemy 2.0 (>=2.0.28), Psycopg 3 (>=3.1.18), PostgreSQL (14+)
- **Settings & Validation:** Pydantic (>=2.6.0), Pydantic Settings (>=2.2.0)
- **Testing & Client:** Pytest (>=8.0.0), HTTPX (>=0.27.0)

---

## 📁 Repository Structure

```text
MediGen-AI/
├── backend/
│   ├── app/
│   │   ├── ai/            # AI pipelines & model integrations (planned)
│   │   ├── api/           # API endpoints & routers (planned)
│   │   ├── core/          # Core configuration & application settings
│   │   │   ├── __init__.py
│   │   │   └── config.py  # Pydantic Settings configuration
│   │   ├── database/      # Database foundation
│   │   │   ├── __init__.py# Export Base, engine, SessionLocal, get_db
│   │   │   ├── base.py    # SQLAlchemy 2.0 DeclarativeBase
│   │   │   ├── connection.py # SQLAlchemy Engine & pool setup
│   │   │   └── session.py # Request-scoped session dependency
│   │   ├── models/        # Database ORM models (planned)
│   │   ├── schemas/       # Pydantic data schemas (planned)
│   │   ├── services/      # Business logic & services (planned)
│   │   ├── __init__.py
│   │   └── main.py        # FastAPI entrypoint & health endpoints
│   ├── tests/             # Automated test suite
│   │   ├── __init__.py
│   │   ├── conftest.py    # Pytest fixtures & TestClient configuration
│   │   ├── test_database_health.py      # Unit tests for /health/db
│   │   ├── test_database_integration.py # Live PostgreSQL integration tests
│   │   └── test_main.py   # Root & app health endpoint tests
│   ├── .env.example       # Environment configuration template
│   ├── pytest.ini         # Pytest configuration
│   └── requirements.txt   # Backend dependencies
├── database/              # Database migrations & schemas (planned)
├── datasets/              # Clinical test datasets (planned)
├── docker/                # Container configurations (planned)
├── docs/                  # Architecture & system documentation
│   └── database.md        # Detailed PostgreSQL database guide
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
# Navigate to the backend directory
cd backend

# Create a Python virtual environment
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

### 3. Configure Local Database & Environment Variables

1. Create the `medigen_ai` database in PostgreSQL (see [`docs/database.md`](docs/database.md) for step-by-step Windows instructions).
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Update `DATABASE_URL` in `.env` with your PostgreSQL password:
   ```env
   DATABASE_URL="postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/medigen_ai"
   ```

### 4. Start the FastAPI Development Server

```bash
# Run with Uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or run via Python module
python -m app.main
```

The API will be available at:
- **Root Endpoint:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Application Health:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Database Health:** [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db)
- **Interactive Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run the automated test suite with `pytest`:

```bash
# Run unit tests (no active database required)
pytest -v

# Run including live PostgreSQL integration tests (requires live database)
RUN_DB_INTEGRATION_TESTS=1 pytest -v
```

---

## 📡 API Endpoints

| Method | Endpoint | Description | Status Code | Response Example |
|---|---|---|---|---|
| `GET` | `/` | API Root / Welcome Message | `200 OK` | `{"message": "Welcome to MediGen AI API", "status": "running"}` |
| `GET` | `/health` | Application Health Check | `200 OK` | `{"status": "healthy"}` |
| `GET` | `/health/db` | Database Health Check | `200 OK` / `503 Unavailable` | `{"status": "healthy", "database": "connected"}` |
| `GET` | `/docs` | OpenAPI / Swagger UI | `200 OK` | Interactive API documentation |
| `GET` | `/redoc` | ReDoc API Documentation | `200 OK` | Alternative interactive API documentation |

---

## 🗺️ Project Roadmap & Planned Milestones

1. **Milestone 1: Backend Foundation** *(Completed & Pushed)* ✅
2. **Milestone 2: Database Layer & Relational Modeling** *(Implemented & Ready for Review)* ✅
3. **Milestone 3: Authentication & Role-Based Access Control** *(Planned)*
4. **Milestone 4: Patient & Electronic Health Records Management** *(Planned)*
5. **Milestone 5: Clinical Retrieval-Augmented Generation (RAG) & Document Analysis** *(Planned)*
6. **Milestone 6: Clinical Frontend Dashboard** *(Planned)*
7. **Milestone 7: End-to-End Testing, Security Audits, and Production Deployment** *(Planned)*
