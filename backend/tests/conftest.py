from collections.abc import Generator
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.database import Base, get_db
from app.main import app

# SQLite in-memory engine shared across threads for deterministic testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create fresh database tables for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def patch_session_local_for_tests():
    """Ensure all background worker jobs and services use the in-memory TestingSessionLocal."""
    patches = [
        patch("app.database.connection.SessionLocal", TestingSessionLocal),
        patch("app.database.session.SessionLocal", TestingSessionLocal),
        patch("app.database.SessionLocal", TestingSessionLocal),
        patch("app.services.task_service.SessionLocal", TestingSessionLocal),
        patch("app.services.quality_service.SessionLocal", TestingSessionLocal),
        patch("app.services.order_service.SessionLocal", TestingSessionLocal),
        patch("app.services.note_service.SessionLocal", TestingSessionLocal),
        patch("app.services.media_service.SessionLocal", TestingSessionLocal),
        patch("app.services.handoff_service.SessionLocal", TestingSessionLocal),
        patch("app.services.cohort_service.SessionLocal", TestingSessionLocal),
        patch("app.services.care_plan_service.SessionLocal", TestingSessionLocal),
        patch("app.tasks.outbox_tasks.SessionLocal", TestingSessionLocal),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in reversed(patches):
            p.stop()


@pytest.fixture(autouse=True)
def configure_test_task_provider():
    """Ensure tests run background tasks synchronously by default to eliminate thread race conditions."""
    from app.ai.task_worker import (
        SyncBackgroundTaskProvider,
        set_background_task_provider,
        reset_background_task_provider,
    )
    set_background_task_provider(SyncBackgroundTaskProvider())
    yield
    reset_background_task_provider()


@pytest.fixture(autouse=True)
def patch_vector_store_for_tests():
    """
    Auto-applied fixture: redirect ChromaDB and embedding provider to
    an ephemeral in-memory store for every test so no shared state or production
    data directories are touched during test runs.

    Uses ephemeral in-memory ChromaDB with unique collection names per test
    to completely isolate vector state across tests.
    """
    import uuid
    from app.ai.embeddings import MockEmbeddingProvider
    from app.ai.vector_store import ChromaVectorStore

    _tmp_store = ChromaVectorStore(
        db_path=None,
        collection_name=f"test_medical_docs_{uuid.uuid4().hex}",
    )
    _mock_provider = MockEmbeddingProvider(dimension=64)



    def _patched_get_vector_store(*args, **kwargs):
        return _tmp_store

    def _patched_get_embedding_provider(*args, **kwargs):
        return _mock_provider

    with (
        patch(
            "app.ai.vector_store.get_vector_store",
            side_effect=_patched_get_vector_store,
        ),
        patch(
            "app.ai.embeddings.get_embedding_provider",
            side_effect=_patched_get_embedding_provider,
        ),
        patch(
            "app.services.document_processing_service.get_vector_store",
            side_effect=_patched_get_vector_store,
        ),
        patch(
            "app.services.document_processing_service.get_embedding_provider",
            side_effect=_patched_get_embedding_provider,
        ),
        patch(
            "app.services.rag_service.get_vector_store",
            side_effect=_patched_get_vector_store,
        ),
        patch(
            "app.services.rag_service.get_embedding_provider",
            side_effect=_patched_get_embedding_provider,
        ),
    ):
        yield

    # Explicitly release ChromaDB file handles before tmp_path cleanup
    try:
        if hasattr(_tmp_store, "_client") and _tmp_store._client is not None:
            _tmp_store._client = None
            _tmp_store._collection = None
    except Exception:
        pass


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient fixture with get_db dependency overridden to use in-memory test session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_admin(db_session: Session):
    """Create a default test admin user."""
    from app.schemas.user import UserRegisterRequest, UserRole
    from app.services.user_service import create_user

    user_in = UserRegisterRequest(
        name="Admin FHIR",
        email="admin_fhir@example.com",
        password="AdminPassword123!",
        role=UserRole.ADMIN,
    )
    return create_user(db_session, user_in)


@pytest.fixture(scope="function")
def test_patient_user(db_session: Session):
    """Create a default patient user account."""
    from app.schemas.user import UserRegisterRequest, UserRole
    from app.services.user_service import create_user

    user_in = UserRegisterRequest(
        name="John Doe",
        email="patient_fhir@example.com",
        password="PatientPassword123!",
        role=UserRole.PATIENT,
    )
    return create_user(db_session, user_in)


@pytest.fixture(scope="function")
def test_patient(db_session: Session, test_patient_user):
    """Create a default patient record linked to test_patient_user."""
    from datetime import date
    from app.models.patient import Patient
    from app.schemas.patient import Gender, PatientStatus

    patient = Patient(
        patient_id="PAT-FHIR-TEST-0001",
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1985, 4, 12),
        gender=Gender.MALE,
        phone="+1-555-0100",
        email=test_patient_user.email,
        address="100 Medical Center Way, Boston, MA",
        emergency_contact_name="Jane Doe",
        emergency_contact_phone="+1-555-0101",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture(scope="function")
def test_doctor_user(db_session: Session):
    """Create a verified doctor user and doctor profile."""
    from app.models.doctor import Doctor
    from app.schemas.doctor import DoctorAvailabilityStatus, DoctorVerificationStatus
    from app.schemas.user import UserRegisterRequest, UserRole
    from app.services.user_service import create_user

    user_in = UserRegisterRequest(
        name="Dr. Sarah Connor",
        email="doctor_fhir@example.com",
        password="DoctorPassword123!",
        role=UserRole.DOCTOR,
    )
    user = create_user(db_session, user_in)

    doc = Doctor(
        doctor_id="DOC-FHIR-0001",
        user_id=user.id,
        full_name="Dr. Sarah Connor",
        specialization="Cardiology",
        medical_registration_number="MED-FHIR-REG-001",
        qualifications="MD Cardiology",
        years_of_experience=10,
        email="doctor_fhir@example.com",
        phone="+1-555-0144",
        department="Cardiology",
        verification_status=DoctorVerificationStatus.VERIFIED,
        availability_status=DoctorAvailabilityStatus.AVAILABLE,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return user
