# MediGen AI - Clinical Decision Support System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
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

**Current Milestone:** `Milestone 1 — Initial Backend Foundation` (Completed)

- [x] Backend directory and package structure initialized
- [x] FastAPI application core configured with CORS middleware
- [x] Environment configuration management implemented using Pydantic Settings
- [x] Automated test suite configured with Pytest and TestClient
- [x] Health check and root API endpoints verified
- [x] Local development environment established with Uvicorn

---

## 🛠️ Technology Stack (Milestone 1)

- **Language:** Python 3.11+
- **API Framework:** FastAPI (>=0.110.0)
- **ASGI Server:** Uvicorn (>=0.28.0)
- **Data Validation & Settings:** Pydantic (>=2.6.0), Pydantic Settings (>=2.2.0)
- **Testing & HTTP Client:** Pytest (>=8.0.0), HTTPX (>=0.27.0)

---

## 📁 Repository Structure

```text
MediGen-AI/
├── backend/
│   ├── app/
│   │   ├── ai/            # AI pipelines & model integrations (future milestones)
│   │   ├── api/           # API endpoints & routers (future milestones)
│   │   ├── core/          # Core configuration & application settings
│   │   ├── database/      # Database sessions & connections (future milestones)
│   │   ├── models/        # Database ORM models (future milestones)
│   │   ├── schemas/       # Pydantic data schemas (future milestones)
│   │   ├── services/      # Business logic & services (future milestones)
│   │   ├── __init__.py
│   │   └── main.py        # FastAPI entrypoint & application initialization
│   ├── tests/             # Automated test suite
│   │   ├── __init__.py
│   │   ├── conftest.py    # Pytest fixtures & TestClient configuration
│   │   └── test_main.py   # Root & health endpoint test cases
│   ├── .env.example       # Environment configuration template
│   ├── pytest.ini         # Pytest configuration
│   └── requirements.txt   # Milestone 1 backend dependencies
├── database/              # Database migrations & schemas (planned)
├── datasets/              # Clinical test datasets (planned)
├── docker/                # Container configurations (planned)
├── docs/                  # Architecture & system documentation (planned)
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

### 3. Configure Environment Variables

```bash
# Copy example configuration file
cp .env.example .env
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
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run the automated test suite with `pytest`:

```bash
# Run tests from the backend directory
pytest

# Run tests with verbose output
pytest -v
```

---

## 📡 API Endpoints (Milestone 1)

| Method | Endpoint | Description | Response Example |
|---|---|---|---|
| `GET` | `/` | API Root / Welcome Message | `{"message": "Welcome to MediGen AI API", "status": "running"}` |
| `GET` | `/health` | Application Health Check | `{"status": "healthy"}` |
| `GET` | `/docs` | OpenAPI / Swagger UI | Interactive API documentation |
| `GET` | `/redoc` | ReDoc API Documentation | Alternative interactive API documentation |

---

## 🗺️ Project Roadmap & Planned Milestones

1. **Milestone 1: Backend Foundation** *(Completed)*
   - FastAPI core initialization, environment settings, automated testing, and health endpoints.
2. **Milestone 2: Database Layer & Relational Modeling** *(Planned)*
   - PostgreSQL integration, SQLAlchemy 2.0 ORM, and Alembic migrations.
3. **Milestone 3: Authentication & Role-Based Access Control** *(Planned)*
   - JWT-based authentication, user roles (Clinician, Radiologist, Admin).
4. **Milestone 4: Patient & Electronic Health Records Management** *(Planned)*
   - Patient profiling, encounter logging, and clinical record management.
5. **Milestone 5: Clinical Retrieval-Augmented Generation (RAG) & Document Analysis** *(Planned)*
   - Medical guideline embedding, vector search, clinical document analysis, and assistive summarization.
6. **Milestone 6: Clinical Frontend Dashboard** *(Planned)*
   - Modern responsive web interface for healthcare professionals.
7. **Milestone 7: End-to-End Testing, Security Audits, and Production Deployment** *(Planned)*
   - Full containerization, HIPAA/GDPR compliance checks, and cloud deployment.
