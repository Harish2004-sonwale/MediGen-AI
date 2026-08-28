# MediGen AI — PostgreSQL Database Guide & Architecture

This document provides a beginner-friendly, comprehensive guide to the database architecture for **MediGen AI** (Clinical Decision Support System).

---

## 1. Core Concepts Explained

### 1.1 Why PostgreSQL for MediGen AI?
In healthcare software, patient records, diagnostic notes, clinical encounters, and audit trails require maximum reliability:
- **ACID Compliance**: Guarantees that medical transactions are recorded completely and accurately without partial data corruption.
- **Relational Integrity**: Enforces strict relationships (e.g., medical records link to valid patients and clinicians).
- **JSONB Support**: Stores semi-structured clinical documentation (e.g., dynamic lab test outputs or medical equipment payloads) efficiently with indexing.
- **Future AI / Vector Search**: Supports extensions like `pgvector` to store vector embeddings for clinical retrieval-augmented generation (RAG).

### 1.2 What is SQLAlchemy?
**SQLAlchemy 2.0** is the standard Python Object-Relational Mapper (ORM) and database toolkit:
- It translates Python objects and operations into SQL queries.
- It manages the **Engine** (connection pool) and **Sessions** (units of work per web request).
- It provides a `DeclarativeBase` so future tables (Patients, Encounters, Records) can be defined cleanly as Python classes.

### 1.3 What is Psycopg?
**Psycopg 3 (`psycopg[binary]`)** is the official database driver for PostgreSQL in Python:
- While SQLAlchemy provides the high-level interface, Psycopg handles the actual network communication with the PostgreSQL database server.

### 1.4 What does `DATABASE_URL` Mean?
The `DATABASE_URL` is a standardized connection string telling SQLAlchemy how to reach your database:

```text
postgresql+psycopg://<username>:<password>@<host>:<port>/<database_name>
```

- **`postgresql+psycopg://`**: Tells SQLAlchemy to connect to PostgreSQL using the Psycopg 3 driver.
- **`<username>`**: Your PostgreSQL user (default is usually `postgres`).
- **`<password>`**: Your PostgreSQL password set during installation.
- **`<host>`**: The database server address (usually `localhost` or `127.0.0.1` for local development).
- **`<port>`**: The port PostgreSQL listens on (standard is `5432`).
- **`<database_name>`**: The target database name (`medigen_ai`).

---

## 2. Database Module Structure

Inside [`backend/app/database/`](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/database/):

```text
backend/app/database/
├── __init__.py     # Exports Base, engine, SessionLocal, and get_db
├── base.py         # SQLAlchemy 2.0 DeclarativeBase for future ORM models
├── connection.py   # SQLAlchemy Engine with connection pool & timeout settings
└── session.py      # FastAPI dependency (get_db) managing request-scoped sessions
```

### Request Session Lifecycle:
1. When a request hits an endpoint needing database access, FastAPI calls `get_db()`.
2. A database session is yielded to the route handler.
3. When the route handler finishes, the `finally` block in `get_db()` automatically runs `db.close()`, returning the connection safely back to the pool.

---

## 3. Step-by-Step Windows PostgreSQL Setup

### Step A: Check if PostgreSQL is Running
You can verify whether PostgreSQL is running on Windows using either of the following methods:

**Method 1: Using Windows Services Manager (GUI)**
1. Press `Win + R`, type `services.msc`, and press Enter.
2. Scroll down and look for **postgresql-x64-<version>** (e.g., `postgresql-x64-16` or `postgresql-x64-15`).
3. Check its Status column:
   - If it says **Running**, PostgreSQL is active.
   - If it is stopped, right-click the service and click **Start**.

**Method 2: Using PowerShell (Command Line)**
Run in PowerShell:
```powershell
Get-Service -Name *postgres*
```

---

### Step B: Create the `medigen_ai` Database

You can create the database using **SQL Shell (psql)** or **pgAdmin 4**:

#### Option 1: Using SQL Shell (psql)
1. Open the Start menu, search for **SQL Shell (psql)**, and launch it.
2. Press Enter to accept defaults for Server (`localhost`), Database (`postgres`), Port (`5432`), and Username (`postgres`).
3. Enter your PostgreSQL password when prompted.
4. Run this SQL command:
   ```sql
   CREATE DATABASE medigen_ai;
   ```
5. Confirm by listing databases:
   ```sql
   \l
   ```
6. Exit the shell:
   ```sql
   \q
   ```

#### Option 2: Using pgAdmin 4 (GUI)
1. Open **pgAdmin 4** from your Start menu.
2. In the left panel, expand **Servers** and enter your master password.
3. Right-click on **Databases** → **Create** → **Database...**.
4. In the Database field, enter: `medigen_ai`.
5. Click **Save**.

---

### Step C: Configure `.env` in Backend

1. In `backend/`, copy `.env.example` to `.env`:
   ```powershell
   cd backend
   Copy-Item .env.example .env
   ```
2. Open `.env` and replace `YOUR_POSTGRES_PASSWORD` with your real PostgreSQL password:
   ```env
   DATABASE_URL="postgresql+psycopg://postgres:YOUR_ACTUAL_PASSWORD@localhost:5432/medigen_ai"
   ```

> [!CAUTION]
> Never commit `.env` to Git. The `.gitignore` file is configured to keep your `.env` private and secure.

---

## 4. Running the Application & Verifying Database Health

### 1. Start the FastAPI Server
```powershell
# From backend directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Verify Database Health Endpoint
Open in your browser or terminal:
- **URL**: `http://127.0.0.1:8000/health/db`

**Expected Responses:**
- **When PostgreSQL is connected (`HTTP 200`):**
  ```json
  {
    "status": "healthy",
    "database": "connected"
  }
  ```
- **When PostgreSQL is offline or unreachable (`HTTP 503`):**
  ```json
  {
    "status": "unhealthy",
    "database": "disconnected",
    "detail": "Database is unreachable or query execution failed"
  }
  ```

---

## 5. Running Automated Tests

```powershell
# Run all unit tests (works out-of-the-box, no live database needed)
pytest -v

# Run live database integration tests (after setting up local PostgreSQL and .env)
$env:RUN_DB_INTEGRATION_TESTS="1"; pytest -v; Remove-Item Env:\RUN_DB_INTEGRATION_TESTS
```
