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


def get_patient_by_user_id(db: Session, user_id: int) -> Patient | None:
    """Retrieve patient record associated with a specific user account."""
    stmt = select(Patient).where(Patient.user_id == user_id)
    return db.scalars(stmt).first()


def get_patient_by_email(db: Session, email: str) -> Patient | None:
    """Retrieve patient record by contact email."""
    stmt = select(Patient).where(func.lower(Patient.email) == email.lower().strip())
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
        blood_group=patient_in.blood_group.strip() if patient_in.blood_group else None,
        allergies=patient_in.allergies.strip() if patient_in.allergies else None,
        health_problem=patient_in.health_problem.strip() if patient_in.health_problem else None,
        previous_diagnoses=patient_in.previous_diagnoses.strip() if patient_in.previous_diagnoses else None,
        current_medications=patient_in.current_medications.strip() if patient_in.current_medications else None,
        assigned_doctor_id=patient_in.assigned_doctor_id,
        user_id=patient_in.user_id,
        facility_id=patient_in.facility_id or "FAC-METRO-MAIN",
        status=patient_in.status,
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def self_register_patient(db: Session, reg_in: any) -> tuple[Patient, any]:
    """Create user account and associated patient profile for new patient onboarding."""
    from app.core.security import hash_password
    from app.models.user import User
    from app.schemas.user import UserRole
    from app.services.user_service import get_user_by_email

    email_clean = reg_in.email.lower().strip()
    existing_user = get_user_by_email(db, email_clean)
    if existing_user:
        raise ValueError(f"An account with email '{email_clean}' is already registered.")

    user = User(
        name=f"{reg_in.first_name.strip()} {reg_in.last_name.strip()}",
        email=email_clean,
        password_hash=hash_password(reg_in.password),
        role=UserRole.PATIENT,
        is_active=True,
        default_facility_id="FAC-METRO-MAIN",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    patient_id = generate_unique_patient_id(db)
    db_patient = Patient(
        patient_id=patient_id,
        first_name=reg_in.first_name.strip(),
        last_name=reg_in.last_name.strip(),
        date_of_birth=reg_in.date_of_birth,
        gender=reg_in.gender,
        phone=reg_in.phone.strip() if reg_in.phone else None,
        email=email_clean,
        address=reg_in.address.strip() if reg_in.address else None,
        emergency_contact_name=reg_in.emergency_contact_name.strip() if reg_in.emergency_contact_name else None,
        emergency_contact_phone=reg_in.emergency_contact_phone.strip() if reg_in.emergency_contact_phone else None,
        blood_group=reg_in.blood_group.strip() if getattr(reg_in, "blood_group", None) else None,
        allergies=reg_in.allergies.strip() if getattr(reg_in, "allergies", None) else None,
        health_problem=reg_in.health_problem.strip() if getattr(reg_in, "health_problem", None) else None,
        previous_diagnoses=reg_in.previous_diagnoses.strip() if getattr(reg_in, "previous_diagnoses", None) else None,
        current_medications=reg_in.current_medications.strip() if getattr(reg_in, "current_medications", None) else None,
        user_id=user.id,
        facility_id="FAC-METRO-MAIN",
        status=PatientStatus.PENDING_REVIEW,
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)

    return db_patient, user


def assign_doctor_to_patient(
    db: Session, patient: Patient, doctor_id: int, notes: str | None = None
) -> Patient:
    """Assign an attending doctor to patient and establish authorized clinical relationship."""
    from app.models.doctor import Doctor
    from app.models.encounter import Encounter

    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise ValueError(f"Doctor profile with ID {doctor_id} does not exist.")

    patient.assigned_doctor_id = doctor.id
    if patient.status == PatientStatus.PENDING_REVIEW:
        patient.status = PatientStatus.ACTIVE

    # Establish or update attending encounter for clinical access / RAG
    enc = (
        db.query(Encounter)
        .filter(Encounter.attending_user_id == doctor.user_id, Encounter.patient_id == patient.id)
        .first()
    )
    if not enc:
        enc = Encounter(
            encounter_id=f"ENC-ADM-{doctor.user_id}-{patient.patient_id}",
            patient_id=patient.id,
            attending_user_id=doctor.user_id,
            chief_complaint=patient.health_problem or "Patient intake & physician assignment",
            assessment=notes or "Assigned by hospital administration for comprehensive care",
            facility_id=patient.facility_id or "FAC-METRO-MAIN",
        )
        db.add(enc)

    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def list_patients(
    db: Session,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status: PatientStatus | None = None,
    doctor_id: int | None = None,
) -> tuple[list[Patient], int]:
    """Retrieve a paginated, filtered list of patients."""
    query = select(Patient)
    count_query = select(func.count(Patient.id))

    filters = []
    if status:
        filters.append(Patient.status == status)

    if doctor_id:
        filters.append(Patient.assigned_doctor_id == doctor_id)

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
        if field == "status" and value is None:
            continue
        if field == "assigned_doctor_id" and value is None:
            continue
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


DEFAULT_DEMO_PATIENTS: list[dict] = []


def seed_default_patients_if_needed(db: Session) -> list[Patient]:
    """No-op: Demo patients disabled for production clean state."""
    return []
