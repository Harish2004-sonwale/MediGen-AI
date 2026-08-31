"""API Endpoints for Multi-Factor Authentication (MFA / TOTP)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.mfa import (
    MFASetupResponse,
    MFAStatusResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
)
from app.services import mfa_service

router = APIRouter(prefix="/auth/mfa", tags=["Multi-Factor Authentication (MFA/TOTP)"])


@router.post("/setup", response_model=MFASetupResponse, summary="Initialize TOTP Secret & Recovery Codes")
def setup_user_mfa(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MFASetupResponse:
    """Generate a new TOTP secret and 10 single-use recovery codes for the authenticated user."""
    result = mfa_service.setup_mfa(db, current_user)
    return MFASetupResponse(**result)


@router.post("/enable", response_model=MFAVerifyResponse, summary="Verify Code and Activate MFA")
def enable_user_mfa(
    payload: MFAVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MFAVerifyResponse:
    """Verify code from authenticator app and enable 2FA on the user's account."""
    success = mfa_service.enable_mfa(db, current_user, payload.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 6-digit TOTP verification code.",
        )
    return MFAVerifyResponse(
        verified=True,
        message="Multi-Factor Authentication has been successfully activated.",
    )


@router.post("/verify", response_model=MFAVerifyResponse, summary="Validate TOTP or Backup Code")
def verify_user_mfa_code(
    payload: MFAVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MFAVerifyResponse:
    """Validate TOTP or backup recovery code during login step."""
    valid, message = mfa_service.verify_mfa_code(db, current_user, payload.code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )
    return MFAVerifyResponse(verified=True, message=message)


@router.post("/disable", response_model=MFAVerifyResponse, summary="Disable MFA")
def disable_user_mfa(
    payload: MFAVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MFAVerifyResponse:
    """Disable MFA after verifying valid code."""
    success = mfa_service.disable_mfa(db, current_user, payload.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation code; could not disable MFA.",
        )
    return MFAVerifyResponse(
        verified=True,
        message="Multi-Factor Authentication has been disabled.",
    )


@router.get("/status", response_model=MFAStatusResponse, summary="Get Current MFA Status")
def get_user_mfa_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MFAStatusResponse:
    """Return user MFA status and remaining backup recovery codes count."""
    status_data = mfa_service.get_mfa_status(db, current_user)
    return MFAStatusResponse(**status_data)
