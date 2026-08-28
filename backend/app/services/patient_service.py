from datetime import datetime
import secrets
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientStatus, PatientUpdate


def generate_unique_patient_id(db: Session) -> str:
    """Generate a unique healthcare patient identifier in the format PAT-YYYYMMDD-XXXX."""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    while True:
        suffix = secrets.token_hex(2).upper()  # 4-character hex suffix
        candidate_id = f"PAT-{date_str}-{suffix}"
        existing = db.scalars(select(Patient.id).where(Patient.patient_id == candidate_id)).first()
        if not existing:
            return candidate_id


def get_patient_by_patient_id(db: Session, patient_id: str) -> Patient | None:
    """Retrieve patient record by public patient_id."""
    stmt = select(Patient).where(Patient.patient_id == patient_id.strip())
    return db.scalars(stmt).first()


def get_patient_by_id(db: Session, id: int) -> Patient | None:
    """Retrieve patient record by internal integer id."""
    stmt = select(Patient).where(Patient.id == id)
    return db.scalars(stmt).first()


def create_patient(db: Session, patient_in: PatientCreate) -> Patient:
    """Create a new patient record."""
    patient_id = patient_in.patient_id.strip() if patient_in.patient_id else generate_unique_patient_id(db)

    # Verify patient_id uniqueness
    existing = get_patient_by_patient_id(db, patient_id=patient_id)
    if existing:
        raise ValueError(f"Patient with identifier '{patient_id}' already exists.")

    db_patient = Patient(
        patient_id=patient_id,
        first_name=patient_in.first_name.strip(),
        last_name=patient_in.last_name.strip(),
        date_of_birth=patient_in.date_of_birth,
        gender=patient_in.gender,
        phone=patient_in.phone.strip() if patient_in.phone else None,
        email=patient_in.email.lower().strip() if patient_in.email else None,
        address=patient_in.address.strip() if patient_in.address else None,
        emergency_contact_name=patient_in.emergency_contact_name.strip() if patient_in.emergency_contact_name else None,
        emergency_contact_phone=patient_in.emergency_contact_phone.strip() if patient_in.emergency_contact_phone else None,
        status=patient_in.status,
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def list_patients(
    db: Session,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status: PatientStatus | None = None,
) -> tuple[list[Patient], int]:
    """Retrieve a paginated, filtered list of patients."""
    query = select(Patient)
    count_query = select(func.count(Patient.id))

    filters = []
    if status:
        filters.append(Patient.status == status)

    if search:
        search_pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Patient.patient_id.ilike(search_pattern),
                Patient.first_name.ilike(search_pattern),
                Patient.last_name.ilike(search_pattern),
                Patient.phone.ilike(search_pattern),
                Patient.email.ilike(search_pattern),
            )
        )

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = db.scalar(count_query) or 0

    # Sort descending by creation date
    query = query.order_by(Patient.created_at.desc())

    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    patients = list(db.scalars(query).all())
    return patients, total


def update_patient(
    db: Session,
    patient: Patient,
    patient_in: PatientUpdate,
) -> Patient:
    """Update patient details, excluding immutable identifiers."""
    update_data = patient_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None and isinstance(value, str):
            value = value.strip()
        setattr(patient, field, value)

    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def deactivate_patient(db: Session, patient: Patient) -> Patient:
    """Soft-delete / deactivate a patient by setting status to inactive."""
    patient.status = PatientStatus.INACTIVE
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient
