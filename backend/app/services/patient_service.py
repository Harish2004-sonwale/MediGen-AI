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


DEFAULT_DEMO_PATIENTS = [
    {
        "patient_id": "PAT-00101",
        "first_name": "Rahul",
        "last_name": "Patil",
        "date_of_birth": datetime(1998, 5, 14).date(),
        "gender": "male",
        "email": "patient@hospital.org",
        "phone": "+91-98200-11223",
        "address": "42 Shivaji Park, Dadar, Mumbai, Maharashtra 400028",
        "emergency_contact_name": "Pooja Patil",
        "emergency_contact_phone": "+91-98200-11224",
        "blood_group": "O+",
        "allergies": "Penicillin",
        "health_problem": "Chest tightness and mild shortness of breath for 2 days after exertion",
        "previous_diagnoses": "Mild hypertension (2024)",
        "current_medications": "Amlodipine 5mg once daily",
        "facility_id": "FAC-METRO-MAIN",
        "status": PatientStatus.ACTIVE,
    },
    {
        "patient_id": "PAT-00102",
        "first_name": "Sneha",
        "last_name": "Kulkarni",
        "date_of_birth": datetime(1992, 7, 19).date(),
        "gender": "female",
        "email": "sneha.kulkarni@example.com",
        "phone": "+91-98200-22334",
        "address": "15 FC Road, Shivajinagar, Pune, Maharashtra 411005",
        "emergency_contact_name": "Vijay Kulkarni",
        "emergency_contact_phone": "+91-98200-22335",
        "blood_group": "AB+",
        "allergies": "Sulfa drugs",
        "health_problem": "High fever and persistent dry cough for 4 days",
        "previous_diagnoses": "Allergic bronchitis",
        "current_medications": "Paracetamol 650mg as needed",
        "facility_id": "FAC-METRO-MAIN",
        "status": PatientStatus.ACTIVE,
    },
    {
        "patient_id": "PAT-00103",
        "first_name": "Amit",
        "last_name": "Jadhav",
        "date_of_birth": datetime(1981, 3, 22).date(),
        "gender": "male",
        "email": "amit.jadhav@example.com",
        "phone": "+91-98200-33445",
        "address": "88 Residency Road, Richmond Town, Bengaluru, Karnataka 560025",
        "emergency_contact_name": "Amol Jadhav",
        "emergency_contact_phone": "+91-98200-33446",
        "blood_group": "A+",
        "allergies": "None",
        "health_problem": "Acute right knee joint pain and swelling after sports injury",
        "previous_diagnoses": "None",
        "current_medications": "None",
        "facility_id": "FAC-METRO-MAIN",
        "status": PatientStatus.ACTIVE,
    },
    {
        "patient_id": "PAT-00104",
        "first_name": "Pooja",
        "last_name": "Deshmukh",
        "date_of_birth": datetime(1995, 10, 25).date(),
        "gender": "female",
        "email": "pooja.deshmukh@example.com",
        "phone": "+91-98200-44556",
        "address": "12 Banjara Hills, Road No 3, Hyderabad, Telangana 500034",
        "emergency_contact_name": "Meera Deshmukh",
        "emergency_contact_phone": "+91-98200-44557",
        "blood_group": "B+",
        "allergies": "Latex",
        "health_problem": "General fatigue and requested baseline health check-up",
        "previous_diagnoses": "None",
        "current_medications": "Multivitamin once daily",
        "facility_id": "FAC-METRO-MAIN",
        "status": PatientStatus.PENDING_REVIEW,
    },
    {
        "patient_id": "PAT-00105",
        "first_name": "Rohan",
        "last_name": "Shinde",
        "date_of_birth": datetime(1971, 11, 8).date(),
        "gender": "male",
        "email": "rohan.shinde@example.com",
        "phone": "+91-98200-55667",
        "address": "74 Park Street, Kolkata, West Bengal 700016",
        "emergency_contact_name": "Anjali Shinde",
        "emergency_contact_phone": "+91-98200-55668",
        "blood_group": "O-",
        "allergies": "Aspirin",
        "health_problem": "Routine follow-up for blood pressure monitoring and prescription renewal",
        "previous_diagnoses": "Essential Hypertension, Dyslipidemia",
        "current_medications": "Telmisartan 40mg, Atorvastatin 10mg",
        "facility_id": "FAC-METRO-MAIN",
        "status": PatientStatus.ACTIVE,
    },
    {
        "patient_id": "PAT-00106",
        "first_name": "Neha",
        "last_name": "Pawar",
        "date_of_birth": datetime(2000, 8, 30).date(),
        "gender": "female",
        "email": "neha.pawar@example.com",
        "phone": "+91-98200-66778",
        "address": "29 Alkapuri, Race Course Road, Vadodara, Gujarat 390007",
        "emergency_contact_name": "Kavita Pawar",
        "emergency_contact_phone": "+91-98200-66779",
        "blood_group": "A-",
        "allergies": "None",
        "health_problem": "Recurrent throbbing migraine headaches on prolonged screen use",
        "previous_diagnoses": "Migraine without aura",
        "current_medications": "Naproxen 500mg as needed",
        "facility_id": "FAC-METRO-MAIN",
        "status": PatientStatus.PENDING_REVIEW,
    },
]


def seed_default_patients_if_needed(db: Session) -> list[Patient]:
    """Ensure standard realistic Indian synthetic demo patient records exist."""
    seeded: list[Patient] = []
    for p_data in DEFAULT_DEMO_PATIENTS:
        existing = get_patient_by_patient_id(db, p_data["patient_id"])
        if not existing:
            patient = Patient(
                patient_id=p_data["patient_id"],
                first_name=p_data["first_name"],
                last_name=p_data["last_name"],
                date_of_birth=p_data["date_of_birth"],
                gender=p_data["gender"],
                email=p_data["email"],
                phone=p_data["phone"],
                address=p_data["address"],
                emergency_contact_name=p_data["emergency_contact_name"],
                emergency_contact_phone=p_data["emergency_contact_phone"],
                blood_group=p_data.get("blood_group"),
                allergies=p_data.get("allergies"),
                health_problem=p_data.get("health_problem"),
                previous_diagnoses=p_data.get("previous_diagnoses"),
                current_medications=p_data.get("current_medications"),
                facility_id=p_data["facility_id"],
                status=p_data["status"],
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            seeded.append(patient)
        else:
            # Update names and demographics for standard presentation
            existing.first_name = p_data["first_name"]
            existing.last_name = p_data["last_name"]
            existing.date_of_birth = p_data["date_of_birth"]
            existing.gender = p_data["gender"]
            existing.email = p_data["email"]
            existing.phone = p_data["phone"]
            existing.address = p_data["address"]
            existing.emergency_contact_name = p_data["emergency_contact_name"]
            existing.emergency_contact_phone = p_data["emergency_contact_phone"]
            existing.blood_group = p_data.get("blood_group")
            existing.allergies = p_data.get("allergies")
            existing.health_problem = p_data.get("health_problem")
            existing.previous_diagnoses = p_data.get("previous_diagnoses")
            existing.current_medications = p_data.get("current_medications")
            existing.status = p_data["status"]
            db.commit()
            db.refresh(existing)
            seeded.append(existing)
    return seeded
