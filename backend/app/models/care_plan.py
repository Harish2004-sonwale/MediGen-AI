"""SQLAlchemy model for Clinical Care Plans."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.schemas.care_plan import CarePlanCategory, CarePlanStatus

if TYPE_CHECKING:
    from app.models.care_task import CareTask
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from app.models.user import User


class CarePlan(Base):
    """CarePlan ORM model storing structured clinical care plans, goals, and interventions."""

    __tablename__ = "care_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    author_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    encounter_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("encounters.id", ondelete="SET NULL"),
        nullable=True,
    )
    facility_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True, default="FAC-001")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[CarePlanCategory] = mapped_column(
        Enum(
            CarePlanCategory,
            name="care_plan_category",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CarePlanCategory.CHRONIC_DISEASE_MANAGEMENT,
        nullable=False,
    )
    status: Mapped[CarePlanStatus] = mapped_column(
        Enum(
            CarePlanStatus,
            name="care_plan_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CarePlanStatus.DRAFT,
        index=True,
        nullable=False,
    )
    intent: Mapped[str] = mapped_column(String(30), default="plan", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    goals_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    interventions_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # AI & Review Metadata
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", backref="care_plans")
    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_user_id])
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])
    encounter: Mapped[Optional["Encounter"]] = relationship("Encounter")
    tasks: Mapped[list["CareTask"]] = relationship("CareTask", back_populates="care_plan", cascade="all, delete-orphan")
