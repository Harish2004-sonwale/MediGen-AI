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


DEFAULT_DEMO_USERS = [
    {
        "name": "Dr. Gregory House, MD",
        "email": "doctor@hospital.org",
        "password": "DoctorPassword123!",
        "role": UserRole.DOCTOR,
    },
    {
        "name": "System Administrator",
        "email": "admin@hospital.org",
        "password": "AdminPassword123!",
        "role": UserRole.ADMIN,
    },
    {
        "name": "Eleanor Vance",
        "email": "patient@hospital.org",
        "password": "PatientPassword123!",
        "role": UserRole.PATIENT,
    },
    {
        "name": "Dr. John Watson",
        "email": "doctor@example.com",
        "password": "DoctorPassword123!",
        "role": UserRole.DOCTOR,
    },
    {
        "name": "System Administrator",
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "role": UserRole.ADMIN,
    },
    {
        "name": "Alice Smith",
        "email": "patient@example.com",
        "password": "PatientPassword123!",
        "role": UserRole.PATIENT,
    },
]


def seed_default_users_if_needed(db: Session) -> list[User]:
    """Ensure standard demo users exist with valid password hashes for instant offline demo."""
    seeded: list[User] = []
    for demo in DEFAULT_DEMO_USERS:
        existing = get_user_by_email(db, demo["email"])
        if not existing:
            user = User(
                name=demo["name"],
                email=demo["email"].lower().strip(),
                password_hash=hash_password(demo["password"]),
                role=demo["role"],
                is_active=True,
                default_facility_id="FAC-METRO-MAIN",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            seeded.append(user)
        else:
            if not verify_password(demo["password"], existing.password_hash):
                existing.password_hash = hash_password(demo["password"])
                existing.is_active = True
                db.commit()
                db.refresh(existing)
            seeded.append(existing)
    return seeded

