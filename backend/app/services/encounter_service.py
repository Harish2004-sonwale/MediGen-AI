from datetime import datetime
import secrets
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.encounter import Encounter
from app.models.patient import Patient
from app.schemas.encounter import EncounterCreate, EncounterStatus, EncounterUpdate
from app.services.patient_service import get_patient_by_patient_id


def generate_unique_encounter_id(db: Session) -> str:
    """Generate a unique clinical encounter identifier in the format ENC-YYYYMMDD-XXXX."""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    while True:
        suffix = secrets.token_hex(2).upper()
        candidate_id = f"ENC-{date_str}-{suffix}"
        existing = db.scalars(select(Encounter.id).where(Encounter.encounter_id == candidate_id)).first()
        if not existing:
            return candidate_id


def create_encounter(
    db: Session,
    patient_public_id: str,
    encounter_in: EncounterCreate,
    attending_user_id: int | None = None,
) -> Encounter:
    """Create and record a new clinical encounter for a patient."""
    patient = get_patient_by_patient_id(db, patient_id=patient_public_id)
    if not patient:
        raise ValueError(f"Patient with identifier '{patient_public_id}' was not found.")

    encounter_id = generate_unique_encounter_id(db)
    encounter_date = encounter_in.encounter_date or datetime.utcnow()

    db_encounter = Encounter(
        encounter_id=encounter_id,
        patient_id=patient.id,
        attending_user_id=attending_user_id,
        encounter_date=encounter_date,
        encounter_type=encounter_in.encounter_type,
        chief_complaint=encounter_in.chief_complaint.strip(),
        clinical_notes=encounter_in.clinical_notes.strip() if encounter_in.clinical_notes else None,
        assessment=encounter_in.assessment.strip() if encounter_in.assessment else None,
        plan=encounter_in.plan.strip() if encounter_in.plan else None,
        status=encounter_in.status,
    )
    db.add(db_encounter)
    db.commit()
    db.refresh(db_encounter)
    return db_encounter


def get_encounter_by_encounter_id(db: Session, encounter_id: str) -> Encounter | None:
    """Retrieve an encounter record by public encounter_id."""
    stmt = select(Encounter).where(Encounter.encounter_id == encounter_id.strip())
    return db.scalars(stmt).first()


def get_encounter_by_id(db: Session, id: int) -> Encounter | None:
    """Retrieve an encounter record by internal integer id."""
    stmt = select(Encounter).where(Encounter.id == id)
    return db.scalars(stmt).first()


def list_patient_encounters(
    db: Session,
    patient_public_id: str,
    page: int = 1,
    size: int = 20,
    status: EncounterStatus | None = None,
) -> tuple[list[Encounter], int]:
    """Retrieve paginated clinical encounters for a given patient."""
    patient = get_patient_by_patient_id(db, patient_id=patient_public_id)
    if not patient:
        raise ValueError(f"Patient with identifier '{patient_public_id}' was not found.")

    query = select(Encounter).where(Encounter.patient_id == patient.id)
    count_query = select(func.count(Encounter.id)).where(Encounter.patient_id == patient.id)

    if status:
        query = query.where(Encounter.status == status)
        count_query = count_query.where(Encounter.status == status)

    total = db.scalar(count_query) or 0

    # Sort descending by encounter date, then created_at
    query = query.order_by(Encounter.encounter_date.desc(), Encounter.created_at.desc())

    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    encounters = list(db.scalars(query).all())
    return encounters, total


def update_encounter(
    db: Session,
    encounter: Encounter,
    encounter_in: EncounterUpdate,
) -> Encounter:
    """Update clinical encounter fields, protecting immutable identifiers."""
    update_data = encounter_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None and isinstance(value, str):
            value = value.strip()
        setattr(encounter, field, value)

    db.add(encounter)
    db.commit()
    db.refresh(encounter)
    return encounter
