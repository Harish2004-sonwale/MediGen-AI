from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    HEALTHCARE_STAFF = "healthcare_staff"


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name of the user")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Plain text password (min 8 chars)")
    role: UserRole = Field(
        default=UserRole.HEALTHCARE_STAFF,
        description="Assigned system role (admin, doctor, healthcare_staff)",
    )


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
