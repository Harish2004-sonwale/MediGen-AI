"""Tests for Secure Authentication, RBAC, and Account Deletion Safeguards."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserRole


def test_auth_login_success(client: TestClient, db_session: Session):
    """Verify that a valid active user can log in with correct credentials."""
    user = User(
        email="doctor.active@hospital.org",
        name="Dr. Active Clinician",
        password_hash=hash_password("ValidPassword123!"),
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "doctor.active@hospital.org", "password": "ValidPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "doctor.active@hospital.org"


def test_auth_login_invalid_email(client: TestClient, db_session: Session):
    """Verify that an invalid email returns 401 with standard notification message."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@hospital.org", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "User not found or invalid email/password."


def test_auth_login_invalid_password(client: TestClient, db_session: Session):
    """Verify that a wrong password returns 401 with the exact same notification message."""
    user = User(
        email="patient.real@hospital.org",
        name="Real Patient",
        password_hash=hash_password("CorrectPassword123!"),
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "patient.real@hospital.org", "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "User not found or invalid email/password."


def test_auth_login_inactive_account(client: TestClient, db_session: Session):
    """Verify that an inactive account with correct password returns 403 notification."""
    user = User(
        email="inactive.user@hospital.org",
        name="Inactive User",
        password_hash=hash_password("CorrectPassword123!"),
        role=UserRole.PATIENT,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive.user@hospital.org", "password": "CorrectPassword123!"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Your account is inactive. Please contact the hospital administrator."


def test_account_deletion_success(client: TestClient, db_session: Session):
    """Verify that a user can delete/deactivate their own account with re-authentication."""
    user = User(
        email="delete.me@hospital.org",
        name="User To Delete",
        password_hash=hash_password("PasswordToDelete123!"),
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Login to get token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "delete.me@hospital.org", "password": "PasswordToDelete123!"},
    )
    token = login_res.json()["access_token"]

    # Delete account
    del_res = client.post(
        "/api/v1/auth/delete-account",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "PasswordToDelete123!", "confirmation": "DELETE"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Your account has been deleted successfully."

    # Verify user is now inactive
    db_session.refresh(user)
    assert user.is_active is False

    # Verify deactivated user cannot log in
    retry_login = client.post(
        "/api/v1/auth/login",
        json={"email": "delete.me@hospital.org", "password": "PasswordToDelete123!"},
    )
    assert retry_login.status_code == 403


def test_account_deletion_wrong_password(client: TestClient, db_session: Session):
    """Verify that account deletion fails if re-authentication password is wrong."""
    user = User(
        email="safe.user@hospital.org",
        name="Safe User",
        password_hash=hash_password("RealPassword123!"),
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "safe.user@hospital.org", "password": "RealPassword123!"},
    )
    token = login_res.json()["access_token"]

    del_res = client.post(
        "/api/v1/auth/delete-account",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "WrongPassword999!", "confirmation": "DELETE"},
    )
    assert del_res.status_code == 401
    assert "Invalid password" in del_res.json()["detail"]


def test_last_admin_account_deletion_prohibited(client: TestClient, db_session: Session):
    """Verify that an administrator cannot delete the last active administrator account."""
    admin = User(
        email="sole.admin@hospital.org",
        name="Sole Administrator",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "sole.admin@hospital.org", "password": "AdminPass123!"},
    )
    token = login_res.json()["access_token"]

    del_res = client.post(
        "/api/v1/auth/delete-account",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "AdminPass123!", "confirmation": "DELETE"},
    )
    assert del_res.status_code == 400
    assert "last active system administrator" in del_res.json()["detail"]
