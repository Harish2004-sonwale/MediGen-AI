from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.security import create_access_token
from app.database import get_db
from app.models.user import User
from app.schemas.token import TokenResponse
from app.schemas.user import (
    AccountDeletionRequest,
    AccountDeletionResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    delete_user_account,
    get_user_by_email,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    user_in: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    """Register a new healthcare professional or administrator."""
    existing_user = get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )
    return create_user(db, user_in=user_in)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT token",
)
def login(
    login_in: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user credentials and return a signed JWT access token."""
    user = authenticate_user(db, email=login_in.email, password=login_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or invalid email/password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Please contact the hospital administrator.",
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role.value,
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/delete-account",
    response_model=AccountDeletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently delete or deactivate user account with password verification",
)
def delete_account(
    deletion_in: AccountDeletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AccountDeletionResponse:
    """Safely deactivate/delete the current user account requiring password verification and safeguards."""
    if deletion_in.confirmation.strip().upper() != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation text must be 'DELETE'.",
        )
    try:
        delete_user_account(db, user=current_user, password=deletion_in.password)
        return AccountDeletionResponse(
            message="Your account has been deleted successfully.",
            status="success",
        )
    except ValueError as exc:
        err_msg = str(exc)
        if "Invalid password" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=err_msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        ) from exc


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Retrieve profile information for the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Authentication module health check",
)
def auth_health() -> dict[str, str]:
    """Check health status of the authentication module."""
    return {
        "status": "healthy",
        "module": "auth",
    }
