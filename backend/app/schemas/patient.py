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
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    APPOINTMENT_SCHEDULED = "appointment_scheduled"
    UNDER_CARE = "under_care"
    DISCHARGED = "discharged"
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
    blood_group: str | None = Field(default=None, max_length=10, description="Blood group (e.g. O+, A+, B+)")
    allergies: str | None = Field(default=None, max_length=255, description="Known allergies")
    health_problem: str | None = Field(default=None, max_length=1000, description="What problem are you having?")
    previous_diagnoses: str | None = Field(default=None, max_length=1000, description="Previous health problems")
    current_medications: str | None = Field(default=None, max_length=1000, description="Current medicines")
    assigned_doctor_id: int | None = Field(default=None, description="Assigned doctor ID")
    assigned_doctor_name: str | None = Field(default=None, description="Assigned doctor name")
    user_id: int | None = Field(default=None, description="Linked user account ID")
    facility_id: str | None = Field(default="FAC-001", description="Assigned facility ID")


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


class PatientSelfRegister(BaseModel):
    """Patient self-registration form on public portal."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: Gender
    phone: str = Field(..., min_length=5, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8)
    address: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    blood_group: str | None = Field(default=None, max_length=10)
    allergies: str | None = Field(default=None, max_length=255)
    health_problem: str | None = Field(default=None, max_length=1000, description="What problem are you having?")
    previous_diagnoses: str | None = Field(default=None, max_length=1000)
    current_medications: str | None = Field(default=None, max_length=1000)


class PatientAssignDoctorRequest(BaseModel):
    doctor_id: int = Field(..., description="Target doctor profile ID to assign")
    notes: str | None = Field(default=None, description="Administrative assignment rationale")


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
    blood_group: str | None = None
    allergies: str | None = None
    health_problem: str | None = None
    previous_diagnoses: str | None = None
    current_medications: str | None = None
    assigned_doctor_id: int | None = None
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
