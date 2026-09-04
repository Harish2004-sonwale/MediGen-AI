from datetime import datetime
from enum import Enum
import math
from typing import Union
from pydantic import BaseModel, ConfigDict, Field


class DoctorVerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    INACTIVE = "inactive"


class DoctorAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    ON_LEAVE = "on_leave"
    UNAVAILABLE = "unavailable"


class ConsultationMode(str, Enum):
    IN_PERSON = "in_person"
    TELEHEALTH = "telehealth"
    BOTH = "both"


class DoctorBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Full professional name")
    professional_title: str = Field(default="Dr.", max_length=50, description="Professional title (e.g. Dr., MD, Prof. Dr.)")
    department: str = Field(
        default="General Medicine",
        min_length=2,
        max_length=100,
        description="Clinical department (e.g. Cardiology, Dentistry, Dermatology, Neurology, Pediatrics)",
    )
    specialization: str = Field(..., min_length=2, max_length=100, description="Medical specialization (e.g. Orthodontist, Interventional Cardiology)")
    qualifications: str | None = Field(default=None, max_length=255, description="Medical qualifications (e.g. MBBS, MD, BDS, MDS)")
    medical_degree: str | None = Field(default=None, max_length=100, description="Primary medical degree")
    medical_registration_number: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Official medical license or registration identifier",
    )
    years_of_experience: int = Field(default=0, ge=0, le=70, description="Years of professional clinical experience")
    phone: str | None = Field(default=None, max_length=30, description="Contact phone number")
    clinic_hospital_name: str | None = Field(default=None, max_length=150, description="Primary hospital or clinic affiliation")
    consultation_location: str | None = Field(default=None, max_length=255, description="Physical consultation address or room")
    consultation_mode: ConsultationMode = Field(
        default=ConsultationMode.IN_PERSON,
        description="Consultation format (in_person, telehealth, both)",
    )
    professional_bio: str | None = Field(default=None, description="Brief professional summary and clinical focus")
    profile_image_url: str | None = Field(default=None, max_length=500, description="Public profile photo URL")


class DoctorCreate(DoctorBase):
    user_id: int | None = Field(
        default=None,
        description="User account ID to associate with this doctor profile (admin can specify, otherwise derived from authenticated doctor)",
    )


class DoctorAdminCreate(DoctorBase):
    email: str = Field(..., min_length=5, max_length=120, description="Doctor's login email address")
    temporary_password: str | None = Field(
        default=None,
        min_length=8,
        description="Initial temporary password or auto-generated if omitted",
    )


class DoctorAdminProvisionResponse(BaseModel):
    doctor: "DoctorDetailResponse"
    temporary_password: str | None = None
    message: str



class DoctorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    professional_title: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, min_length=2, max_length=100)
    specialization: str | None = Field(default=None, min_length=2, max_length=100)
    qualifications: str | None = Field(default=None, max_length=255)
    medical_degree: str | None = Field(default=None, max_length=100)
    years_of_experience: int | None = Field(default=None, ge=0, le=70)
    phone: str | None = Field(default=None, max_length=30)
    clinic_hospital_name: str | None = Field(default=None, max_length=150)
    consultation_location: str | None = Field(default=None, max_length=255)
    consultation_mode: ConsultationMode | None = None
    professional_bio: str | None = None
    profile_image_url: str | None = Field(default=None, max_length=500)
    availability_status: DoctorAvailabilityStatus | None = None


class DoctorAdminUpdate(DoctorUpdate):
    medical_registration_number: str | None = Field(default=None, min_length=2, max_length=100)
    verification_status: DoctorVerificationStatus | None = None
    rejection_reason: str | None = None


class DoctorVerifyRequest(BaseModel):
    note: str | None = Field(default=None, max_length=255, description="Optional verification approval note")


class DoctorRejectRequest(BaseModel):
    rejection_reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Reason for rejecting the doctor verification application",
    )


class DoctorPublicResponse(BaseModel):
    id: int
    doctor_id: str
    full_name: str
    professional_title: str
    department: str
    specialization: str
    qualifications: str | None = None
    medical_degree: str | None = None
    years_of_experience: int
    clinic_hospital_name: str | None = None
    consultation_location: str | None = None
    consultation_mode: ConsultationMode
    professional_bio: str | None = None
    profile_image_url: str | None = None
    verification_status: DoctorVerificationStatus
    availability_status: DoctorAvailabilityStatus

    model_config = ConfigDict(from_attributes=True)


class DoctorDetailResponse(DoctorPublicResponse):
    user_id: int
    email: str
    phone: str | None = None
    medical_registration_number: str
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorListResponse(BaseModel):
    items: list[Union[DoctorDetailResponse, DoctorPublicResponse]]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[Union[DoctorDetailResponse, DoctorPublicResponse]],
        total: int,
        page: int,
        size: int,
    ) -> "DoctorListResponse":
        total_pages = math.ceil(total / size) if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )


DoctorAdminProvisionResponse.model_rebuild()

