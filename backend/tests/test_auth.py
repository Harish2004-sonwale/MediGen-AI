from datetime import timedelta
from fastapi import APIRouter, Depends, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.security import create_access_token, decode_access_token, verify_password
from app.main import app
from app.models.user import User
from app.schemas.user import UserRole
from app.services.user_service import get_user_by_email

# Helper mock router for testing role-based access control
roles_mock_router = APIRouter(prefix="/test-roles")


@roles_mock_router.get("/doctor-only")
def doctor_only_endpoint(user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN))):
    return {"message": "Doctor access granted", "user_id": user.id}


@roles_mock_router.get("/admin-only")
def admin_only_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
    return {"message": "Admin access granted", "user_id": user.id}


app.include_router(roles_mock_router)


def test_auth_health(client: TestClient):
    """Verify GET /api/v1/auth/health returns 200 and healthy status."""
    response = client.get("/api/v1/auth/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy", "module": "auth"}


def test_register_user_success(client: TestClient, db_session: Session):
    """Verify successful user registration and safe response fields."""
    payload = {
        "name": "Dr. Alice Smith",
        "email": "alice.smith@hospital.org",
        "password": "SecurePassword123!",
        "role": "doctor",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["name"] == "Dr. Alice Smith"
    assert data["email"] == "alice.smith@hospital.org"
    assert data["role"] == "doctor"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    # Ensure password and password_hash are NEVER returned
    assert "password" not in data
    assert "password_hash" not in data

    # Verify password in DB is hashed and matches plain text
    user = get_user_by_email(db_session, "alice.smith@hospital.org")
    assert user is not None
    assert user.password_hash != "SecurePassword123!"
    assert verify_password("SecurePassword123!", user.password_hash)


def test_register_duplicate_email_fails(client: TestClient):
    """Verify that registering with an existing email returns 400 Bad Request."""
    payload = {
        "name": "Dr. Bob",
        "email": "bob@hospital.org",
        "password": "Password123!",
        "role": "doctor",
    }
    response1 = client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == status.HTTP_201_CREATED

    response2 = client.post("/api/v1/auth/register", json=payload)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response2.json()["detail"]


def test_register_invalid_data_validation(client: TestClient):
    """Verify that invalid inputs (short password, invalid email) fail with 422."""
    # Short password
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "test@hospital.org",
            "password": "short",
            "role": "doctor",
        },
    )
    assert response.status_code == 422

    # Invalid email format
    response_email = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "not-an-email",
            "password": "ValidPassword123!",
            "role": "doctor",
        },
    )
    assert response_email.status_code == 422


def test_login_success(client: TestClient):
    """Verify login returns valid JWT access token and user info."""
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Staff Member",
            "email": "staff@hospital.org",
            "password": "MySecretPassword123!",
            "role": "healthcare_staff",
        },
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "staff@hospital.org",
            "password": "MySecretPassword123!",
        },
    )
    assert login_response.status_code == status.HTTP_200_OK
    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "staff@hospital.org"
    assert data["user"]["role"] == "healthcare_staff"

    # Decode and verify JWT payload
    payload = decode_access_token(data["access_token"])
    assert payload["sub"] == str(data["user"]["id"])
    assert payload["role"] == "healthcare_staff"


def test_login_invalid_credentials(client: TestClient):
    """Verify login with wrong credentials returns generic 401 without leaking existence."""
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin User",
            "email": "admin@hospital.org",
            "password": "AdminPassword123!",
            "role": "admin",
        },
    )

    # Wrong password
    res_wrong_pw = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hospital.org", "password": "WrongPassword123!"},
    )
    assert res_wrong_pw.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_wrong_pw.json()["detail"] == "User not found or invalid email/password."

    # Non-existent email
    res_no_user = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@hospital.org", "password": "AnyPassword123!"},
    )
    assert res_no_user.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_no_user.json()["detail"] == "User not found or invalid email/password."


def test_get_me_protected_endpoint(client: TestClient):
    """Verify GET /api/v1/auth/me behavior without token, with valid token, and with invalid token."""
    # 1. Without token -> 401 Unauthorized
    res_no_auth = client.get("/api/v1/auth/me")
    assert res_no_auth.status_code == status.HTTP_401_UNAUTHORIZED

    # Register and login
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Dr. House",
            "email": "house@hospital.org",
            "password": "Diagnostician123!",
            "role": "doctor",
        },
    )
    user_id = reg_res.json()["id"]

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "house@hospital.org", "password": "Diagnostician123!"},
    )
    token = login_res.json()["access_token"]

    # 2. With valid token -> 200 OK
    res_auth = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_auth.status_code == status.HTTP_200_OK
    assert res_auth.json()["email"] == "house@hospital.org"
    assert res_auth.json()["id"] == user_id

    # 3. With invalid/tampered token -> 401 Unauthorized
    res_invalid = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert res_invalid.status_code == status.HTTP_401_UNAUTHORIZED

    # 4. With expired token -> 401 Unauthorized
    expired_token = create_access_token(
        subject=user_id,
        role="doctor",
        expires_delta=timedelta(seconds=-10),
    )
    res_expired = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == status.HTTP_401_UNAUTHORIZED


def test_role_based_access_control(client: TestClient):
    """Verify require_role allows authorized roles and rejects unauthorized roles with 403."""
    # Register a healthcare staff user
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Nurse Joy",
            "email": "nurse.joy@hospital.org",
            "password": "NursePassword123!",
            "role": "healthcare_staff",
        },
    )
    staff_login = client.post(
        "/api/v1/auth/login",
        json={"email": "nurse.joy@hospital.org", "password": "NursePassword123!"},
    )
    staff_token = staff_login.json()["access_token"]

    # Register a doctor user
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Dr. Strange",
            "email": "strange@hospital.org",
            "password": "SorcererDoctor123!",
            "role": "doctor",
        },
    )
    doc_login = client.post(
        "/api/v1/auth/login",
        json={"email": "strange@hospital.org", "password": "SorcererDoctor123!"},
    )
    doc_token = doc_login.json()["access_token"]

    # Register an admin user
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin Chief",
            "email": "chief@hospital.org",
            "password": "ChiefPassword123!",
            "role": "admin",
        },
    )
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "chief@hospital.org", "password": "ChiefPassword123!"},
    )
    admin_token = admin_login.json()["access_token"]

    # Test doctor-only endpoint:
    # 1. Staff accessing doctor endpoint -> 403 Forbidden
    res_staff_on_doc = client.get(
        "/test-roles/doctor-only",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert res_staff_on_doc.status_code == status.HTTP_403_FORBIDDEN
    assert "Operation not permitted" in res_staff_on_doc.json()["detail"]

    # 2. Doctor accessing doctor endpoint -> 200 OK
    res_doc_on_doc = client.get(
        "/test-roles/doctor-only",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert res_doc_on_doc.status_code == status.HTTP_200_OK

    # 3. Admin accessing admin endpoint -> 200 OK
    res_admin_on_admin = client.get(
        "/test-roles/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_on_admin.status_code == status.HTTP_200_OK

    # 4. Doctor accessing admin endpoint -> 403 Forbidden
    res_doc_on_admin = client.get(
        "/test-roles/admin-only",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert res_doc_on_admin.status_code == status.HTTP_403_FORBIDDEN
