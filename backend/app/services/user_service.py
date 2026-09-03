from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserRegisterRequest, UserRole


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


DEFAULT_DEMO_USERS = [
    {
        "name": "Dr. Amit Kulkarni, MD",
        "email": "doctor@hospital.org",
        "password": "DoctorPassword123!",
        "role": UserRole.DOCTOR,
    },
    {
        "name": "System Administrator",
        "email": "admin@hospital.org",
        "password": "AdminPassword123!",
        "role": UserRole.ADMIN,
    },
    {
        "name": "Rahul Patil",
        "email": "patient@hospital.org",
        "password": "PatientPassword123!",
        "role": UserRole.PATIENT,
    },
    {
        "name": "Dr. Amit Kulkarni",
        "email": "doctor@example.com",
        "password": "DoctorPassword123!",
        "role": UserRole.DOCTOR,
    },
    {
        "name": "System Administrator",
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "role": UserRole.ADMIN,
    },
    {
        "name": "Rahul Patil",
        "email": "patient@example.com",
        "password": "PatientPassword123!",
        "role": UserRole.PATIENT,
    },
    {
        "name": "Dr. Neha Patil, MD",
        "email": "neha.patil@hospital.org",
        "password": "DoctorPassword123!",
        "role": UserRole.DOCTOR,
    },
    {
        "name": "Dr. Sandeep Shinde, MS",
        "email": "sandeep.shinde@hospital.org",
        "password": "DoctorPassword123!",
        "role": UserRole.DOCTOR,
    },
    {
        "name": "Dr. Priya Joshi, MD",
        "email": "priya.joshi@hospital.org",
        "password": "DoctorPassword123!",
        "role": UserRole.DOCTOR,
    },
]


def seed_default_users_if_needed(db: Session) -> list[User]:
    """Ensure standard demo users exist with valid password hashes for instant offline demo."""
    from app.models.doctor import Doctor
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from app.services.patient_service import seed_default_patients_if_needed

    seeded: list[User] = []
    doctor_users: list[User] = []

    for demo in DEFAULT_DEMO_USERS:
        existing = get_user_by_email(db, demo["email"])
        if not existing:
            user = User(
                name=demo["name"],
                email=demo["email"].lower().strip(),
                password_hash=hash_password(demo["password"]),
                role=demo["role"],
                is_active=True,
                default_facility_id="FAC-METRO-MAIN",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            seeded.append(user)
            if user.role == UserRole.DOCTOR:
                doctor_users.append(user)
        else:
            existing.name = demo["name"]
            if not verify_password(demo["password"], existing.password_hash):
                existing.password_hash = hash_password(demo["password"])
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            seeded.append(existing)
            if existing.role == UserRole.DOCTOR:
                doctor_users.append(existing)

    # Doctor specialization directory
    DOC_SPECIALIZATIONS = {
        "doctor@hospital.org": ("Cardiology & Internal Medicine", "Cardiology", "MBBS, MD (Cardiology), FACC"),
        "doctor@example.com": ("Cardiology & Internal Medicine", "Cardiology", "MBBS, MD (Cardiology), FACC"),
        "neha.patil@hospital.org": ("General & Preventive Medicine", "General Medicine", "MBBS, MD (General Medicine)"),
        "sandeep.shinde@hospital.org": ("Orthopedic Surgery & Joint Care", "Orthopedics", "MBBS, MS (Orthopedics)"),
        "priya.joshi@hospital.org": ("Pediatrics & Neonatology", "Pediatrics", "MBBS, MD (Pediatrics), DCH"),
    }

    # 1. Ensure Doctor profiles exist for all doctor users
    for doc_user in doctor_users:
        doc_prof = db.query(Doctor).filter(Doctor.user_id == doc_user.id).first()
        spec_info = DOC_SPECIALIZATIONS.get(
            doc_user.email, ("General Medicine", "General Medicine", "MBBS, MD")
        )
        if not doc_prof:
            doc_prof = Doctor(
                doctor_id=f"DOC-{doc_user.id}",
                user_id=doc_user.id,
                full_name=doc_user.name,
                professional_title="Dr.",
                department=spec_info[1],
                specialization=spec_info[0],
                qualifications=spec_info[2],
                medical_degree="MD",
                medical_registration_number=f"MCI-{doc_user.id:04d}-2026",
                years_of_experience=12,
                email=doc_user.email,
                phone="+91-98200-99999",
            )
            db.add(doc_prof)
            db.commit()
            db.refresh(doc_prof)
        else:
            doc_prof.full_name = doc_user.name
            doc_prof.department = spec_info[1]
            doc_prof.specialization = spec_info[0]
            doc_prof.qualifications = spec_info[2]
            db.commit()

    # 2. Seed default demo patients
    seeded_patients = seed_default_patients_if_needed(db)

    # 3. Link demo patients to primary doctors and user accounts
    primary_doc = db.query(Doctor).filter(Doctor.email == "doctor@hospital.org").first()
    if not primary_doc and doctor_users:
        primary_doc = db.query(Doctor).filter(Doctor.user_id == doctor_users[0].id).first()

    patient_user = db.query(User).filter(User.email == "patient@hospital.org").first()

    for patient in seeded_patients:
        # Link first demo patient to patient user account
        if patient.patient_id == "PAT-00101" and patient_user:
            patient.user_id = patient_user.id

        # Assign primary doctor if active
        if patient.status == PatientStatus.ACTIVE and primary_doc:
            patient.assigned_doctor_id = primary_doc.id

        db.commit()

        # Create attending encounter for clinical access
        if primary_doc:
            enc = db.query(Encounter).filter(
                Encounter.attending_user_id == primary_doc.user_id,
                Encounter.patient_id == patient.id,
            ).first()
            if not enc:
                enc = Encounter(
                    encounter_id=f"ENC-DEMO-{primary_doc.user_id}-{patient.patient_id}",
                    patient_id=patient.id,
                    attending_user_id=primary_doc.user_id,
                    chief_complaint=patient.health_problem or "Comprehensive clinical consultation",
                    facility_id="FAC-METRO-MAIN",
                )
                db.add(enc)
                db.commit()
    return seeded

