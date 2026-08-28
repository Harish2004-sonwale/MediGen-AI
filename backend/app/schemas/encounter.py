from datetime import datetime
from enum import Enum
import math
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EncounterType(str, Enum):
    INITIAL_CONSULTATION = "initial_consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    ROUTINE_CHECKUP = "routine_checkup"
    TELEHEALTH = "telehealth"


class EncounterStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    AMENDED = "amended"
    CANCELLED = "cancelled"


class EncounterBase(BaseModel):
    encounter_type: EncounterType = Field(
        default=EncounterType.INITIAL_CONSULTATION,
        description="Clinical classification of the encounter",
    )
    chief_complaint: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Primary medical reason or symptom for the clinical encounter",
    )
    clinical_notes: str | None = Field(
        default=None,
        description="Clinician examination findings and observations",
    )
    assessment: str | None = Field(
        default=None,
        description="Clinician differential diagnosis and diagnostic assessment",
    )
    plan: str | None = Field(
        default=None,
        description="Recommended management, therapy, prescription, and follow-up plan",
    )
    status: EncounterStatus = Field(
        default=EncounterStatus.COMPLETED,
        description="Encounter workflow status",
    )
    encounter_date: datetime | None = Field(
        default=None,
        description="Date and time of the encounter (defaults to current time if omitted)",
    )


class EncounterCreate(EncounterBase):
    pass


class EncounterUpdate(BaseModel):
    encounter_type: EncounterType | None = None
    chief_complaint: str | None = Field(default=None, min_length=1, max_length=255)
    clinical_notes: str | None = None
    assessment: str | None = None
    plan: str | None = None
    status: EncounterStatus | None = None
    encounter_date: datetime | None = None


class EncounterResponse(EncounterBase):
    id: int
    encounter_id: str
    patient_id: str
    attending_user_id: int | None = None
    attending_user_name: str | None = None
    encounter_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, encounter: object) -> "EncounterResponse":
        """Helper to construct EncounterResponse from ORM model with populated relationships."""
        patient_id = getattr(encounter.patient, "patient_id", str(encounter.patient_id)) if hasattr(encounter, "patient") and encounter.patient else str(encounter.patient_id)
        attending_user_name = encounter.attending_user.name if hasattr(encounter, "attending_user") and encounter.attending_user else None

        return cls(
            id=encounter.id,
            encounter_id=encounter.encounter_id,
            patient_id=patient_id,
            attending_user_id=encounter.attending_user_id,
            attending_user_name=attending_user_name,
            encounter_type=encounter.encounter_type,
            chief_complaint=encounter.chief_complaint,
            clinical_notes=encounter.clinical_notes,
            assessment=encounter.assessment,
            plan=encounter.plan,
            status=encounter.status,
            encounter_date=encounter.encounter_date,
            created_at=encounter.created_at,
            updated_at=encounter.updated_at,
        )


class EncounterListResponse(BaseModel):
    items: list[EncounterResponse]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(cls, items: list[EncounterResponse], total: int, page: int, size: int) -> "EncounterListResponse":
        total_pages = math.ceil(total / size) if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )
