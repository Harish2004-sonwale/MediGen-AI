# MediGen AI — Authentication & Role-Based Access Control (RBAC)

This document provides complete documentation for the authentication and user role architecture in the **MediGen AI Clinical Decision Support System**.

---

## 1. Authentication Architecture Overview

MediGen AI uses stateless **JWT (JSON Web Token)** access tokens paired with **Bcrypt** cryptographic password hashing to provide secure, production-grade authentication for healthcare personnel.

```text
Authentication & Authorization Flow:

1. User Registration:
   Client ──( Name, Email, Password, Role )──► POST /api/v1/auth/register
                                                     │
                                                     ▼
                                            Hash with Bcrypt
                                                     │
                                                     ▼
                                            Save User to Database
                                                     │
                                                     ▼
   Client ◄──( Safe User Profile without Password/Hash )──────

2. User Login:
   Client ──( Email, Password )──────────────► POST /api/v1/auth/login
                                                     │
                                                     ▼
                                            Verify Bcrypt Hash
                                                     │
                                                     ▼
                                            Generate Signed JWT
                                                     │
                                                     ▼
   Client ◄──( Bearer Access Token + Safe Profile )───────────

3. Protected Resource Access:
   Client ──( Authorization: Bearer <token> )─► GET /api/v1/auth/me
                                                     │
                                                     ▼
                                            Validate Signature & Expiry
                                                     │
                                                     ▼
                                            Verify Active Status & Role
                                                     │
                                                     ▼
   Client ◄──( Authorized Resource Payload )──────────────────
```

---

## 2. User Roles

MediGen AI establishes three initial roles for clinical and administrative governance:

| Role | Identifier | Description |
|---|---|---|
| **Administrator** | `admin` | System administrators managing user accounts, auditing, and platform settings. |
| **Doctor** | `doctor` | Licensed physicians and clinicians reviewing diagnostic insights and authoring medical documentation. |
| **Healthcare Staff** | `healthcare_staff` | Nurses, medical assistants, and administrative staff recording encounters and patient details. |

---

## 3. Database Schema (`users` Table)

The user account model is defined in [`app/models/user.py`](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/user.py) and managed via Alembic:

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Unique user identifier |
| `name` | `VARCHAR(100)` | `NOT NULL` | Full name of the user |
| `email` | `VARCHAR(255)` | `UNIQUE`, `NOT NULL`, `INDEX` | Normalized login email |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Salted Bcrypt password hash |
| `role` | `VARCHAR(50)` | `NOT NULL`, Default: `healthcare_staff` | User permission role |
| `is_active` | `BOOLEAN` | `NOT NULL`, Default: `TRUE` | Account status flag |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Account creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NOT NULL`, Default: `now()` | Profile last modified timestamp |

---

## 4. API Endpoints Reference

### 4.1 Register User
- **Endpoint**: `POST /api/v1/auth/register`
- **Access**: Public
- **Request Body**:
  ```json
  {
    "name": "Dr. Sarah Connor",
    "email": "sarah.connor@hospital.org",
    "password": "StrongPassword123!",
    "role": "doctor"
  }
  ```
- **Response (`201 Created`)**:
  ```json
  {
    "id": 1,
    "name": "Dr. Sarah Connor",
    "email": "sarah.connor@hospital.org",
    "role": "doctor",
    "is_active": true,
    "created_at": "2026-08-28T15:35:00.000000Z",
    "updated_at": "2026-08-28T15:35:00.000000Z"
  }
  ```

### 4.2 Login & Obtain JWT Token
- **Endpoint**: `POST /api/v1/auth/login`
- **Access**: Public
- **Request Body**:
  ```json
  {
    "email": "sarah.connor@hospital.org",
    "password": "StrongPassword123!"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "name": "Dr. Sarah Connor",
      "email": "sarah.connor@hospital.org",
      "role": "doctor",
      "is_active": true,
      "created_at": "2026-08-28T15:35:00.000000Z",
      "updated_at": "2026-08-28T15:35:00.000000Z"
    }
  }
  ```

### 4.3 Get Current User Profile (Protected)
- **Endpoint**: `GET /api/v1/auth/me`
- **Access**: Authenticated (Requires `Authorization: Bearer <access_token>`)
- **Response (`200 OK`)**:
  ```json
  {
    "id": 1,
    "name": "Dr. Sarah Connor",
    "email": "sarah.connor@hospital.org",
    "role": "doctor",
    "is_active": true,
    "created_at": "2026-08-28T15:35:00.000000Z",
    "updated_at": "2026-08-28T15:35:00.000000Z"
  }
  ```

### 4.4 Authentication Module Health Check
- **Endpoint**: `GET /api/v1/auth/health`
- **Access**: Public
- **Response (`200 OK`)**:
  ```json
  {
    "status": "healthy",
    "module": "auth"
  }
  ```

---

## 5. Role-Based Access Control in Code

Future endpoints can protect operations using the reusable `require_role` dependency:

```python
from fastapi import APIRouter, Depends
from app.api.deps import require_role
from app.models.user import User
from app.schemas.user import UserRole

router = APIRouter()

@router.get("/clinical-summary")
def get_clinical_summary(
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN))
):
    # Only doctors and admins can reach this block; others receive 403 Forbidden
    return {"message": "Clinical summary data"}
```

---

## 6. Database Migrations with Alembic

Alembic tracks and applies schema modifications cleanly.

### Running Migrations:
```powershell
# Navigate to backend directory
cd backend

# Apply migrations up to latest version
alembic upgrade head
```

### Creating New Revisions (for future models):
```powershell
alembic revision --autogenerate -m "create patients table"
```

---

## 7. Security Best Practices Implemented

1. **Password Hashing**: Bcrypt with unique auto-generated salts. Plaintext passwords never touch database storage.
2. **Safe Response Schemas**: Pydantic models explicitly filter out sensitive fields (`password`, `password_hash`).
3. **Timing-Safe & Generic Error Messages**: Login failures return a generic `"Invalid email or password"` without revealing whether the email or password was wrong, protecting against user enumeration.
4. **Environment Isolation**: JWT secrets, algorithms, and expiration parameters are configured through environment variables.
5. **SQL Injection Prevention**: All database queries utilize SQLAlchemy 2.0 type-safe expressions with parameterized inputs.
