from datetime import date, datetime
from enum import Enum
import math
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class PatientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, description="Patient first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Patient last name")
    date_of_birth: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    gender: Gender = Field(..., description="Gender identifier")
    phone: str | None = Field(default=None, max_length=30, description="Primary contact phone number")
    email: EmailStr | None = Field(default=None, description="Contact email address")
    address: str | None = Field(default=None, max_length=255, description="Residential address")
    emergency_contact_name: str | None = Field(default=None, max_length=100, description="Emergency contact full name")
    emergency_contact_phone: str | None = Field(default=None, max_length=30, description="Emergency contact phone number")


class PatientCreate(PatientBase):
    patient_id: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
        description="Optional custom patient identifier (auto-generated if omitted)",
    )
    status: PatientStatus = Field(
        default=PatientStatus.ACTIVE,
        description="Initial patient status",
    )


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: Gender | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    status: PatientStatus | None = None


class PatientResponse(PatientBase):
    id: int
    patient_id: str
    status: PatientStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(cls, items: list[PatientResponse], total: int, page: int, size: int) -> "PatientListResponse":
        total_pages = math.ceil(total / size) if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )
