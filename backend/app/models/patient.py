from datetime import date, datetime
from sqlalchemy import Date, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.schemas.patient import Gender, PatientStatus


class Patient(Base):
    """Patient ORM model representing patient demographics and profile records."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="patient_gender", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[PatientStatus] = mapped_column(
        Enum(PatientStatus, name="patient_status", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=PatientStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} patient_id={self.patient_id} name={self.first_name} {self.last_name}>"
