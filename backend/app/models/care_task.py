"""SQLAlchemy model for Clinical Care Tasks."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.schemas.care_task import CareTaskStatus, CareTaskType, TaskPriority

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.care_plan import CarePlan
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from app.models.user import User


class CareTask(Base):
    """CareTask ORM model storing actionable clinical follow-ups and workflow tasks."""

    __tablename__ = "care_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    care_plan_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("care_plans.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    encounter_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("encounters.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    appointment_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("appointments.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    assigned_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[CareTaskType] = mapped_column(
        Enum(
            CareTaskType,
            name="care_task_type",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CareTaskType.GENERAL_TASK,
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(
            TaskPriority,
            name="care_task_priority",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=TaskPriority.ROUTINE,
        index=True,
        nullable=False,
    )
    status: Mapped[CareTaskStatus] = mapped_column(
        Enum(
            CareTaskStatus,
            name="care_task_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CareTaskStatus.PENDING,
        index=True,
        nullable=False,
    )
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", backref="care_tasks")
    care_plan: Mapped[Optional["CarePlan"]] = relationship("CarePlan", back_populates="tasks")
    encounter: Mapped[Optional["Encounter"]] = relationship("Encounter")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment")
    assigned_user: Mapped[Optional["User"]] = relationship("User")
