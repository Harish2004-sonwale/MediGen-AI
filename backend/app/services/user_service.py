from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserRegisterRequest


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
