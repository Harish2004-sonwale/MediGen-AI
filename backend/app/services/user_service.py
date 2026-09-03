from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserRegisterRequest, UserRole


def get_user_by_email(db: Session, email: str) -> User | None:
    """Retrieve a user from database by email address."""
    stmt = select(User).where(User.email == email.lower().strip())
    return db.scalars(stmt).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Retrieve a user from database by user ID."""
    stmt = select(User).where(User.id == user_id)
    return db.scalars(stmt).first()


def create_user(db: Session, user_in: UserRegisterRequest) -> User:
    """Create a new user with hashed password."""
    db_user = User(
        name=user_in.name.strip(),
        email=user_in.email.lower().strip(),
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


DEFAULT_DEMO_USERS: list[dict] = []


def seed_default_users_if_needed(db: Session) -> list[User]:
    """No-op: Demo users are disabled for production clean state."""
    return []


def delete_user_account(db: Session, user: User, password: str) -> bool:
    """Safely deactivate/delete user account with credential verification and safeguards."""
    from app.models.doctor import Doctor, DoctorAvailabilityStatus
    from app.models.patient import Patient, PatientStatus
    from app.models.security import AuditAction, AuditOutcome

    # 1. Verify password re-authentication
    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid password. Re-authentication failed.")

    # 2. Prevent accidental deletion of the last active administrator
    if user.role == UserRole.ADMIN:
        active_admins_count = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN, User.is_active.is_(True))
            .count()
        )
        if active_admins_count <= 1:
            raise ValueError(
                "Cannot delete or deactivate the last active system administrator account."
            )

    # 3. Healthcare compliance: mark user inactive to revoke all session/token access
    user.is_active = False

    # Deactivate linked patient profile if present
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if patient:
        patient.status = PatientStatus.INACTIVE

    # Deactivate linked doctor profile if present
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if doctor:
        doctor.availability_status = DoctorAvailabilityStatus.UNAVAILABLE

    db.commit()

    # 4. Audit log event (never storing plaintext passwords or tokens)
    try:
        from app.services.audit_service import AuditService
        AuditService().emit_audit_event(
            db=db,
            action=AuditAction.DELETE,
            resource_type="User",
            resource_id=str(user.id),
            user_id=user.id,
            user_role=user.role.value,
            outcome=AuditOutcome.SUCCESS,
            metadata={"action": "account_deactivation", "email": user.email, "role": user.role.value},
        )
    except Exception:
        pass

    return True

