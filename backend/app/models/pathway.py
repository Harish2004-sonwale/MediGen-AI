"""SQLAlchemy ORM models for Regional Multi-Hospital Clinical Pathways & Care Plan Synchronization."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RegionalClinicalPathway(Base):
    """Represents a standardized regional clinical care pathway definition (e.g. Sepsis, STEMI, ERAS)."""

    __tablename__ = "regional_clinical_pathways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    pathway_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # critical_care, cardiology, oncology, surgery
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="TENANT-001")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    target_duration_hours: Mapped[int] = mapped_column(Integer, default=48, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    stages: Mapped[List["PathwayStage"]] = relationship(
        "PathwayStage",
        back_populates="pathway",
        cascade="all, delete-orphan",
        order_by="PathwayStage.sequence_order",
    )


class PathwayStage(Base):
    """Represents an ordered clinical stage in a pathway with facility ownership and clinical criteria."""

    __tablename__ = "pathway_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    stage_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    pathway_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("regional_clinical_pathways.pathway_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_facility_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    target_duration_minutes: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    required_role: Mapped[str] = mapped_column(String(32), default="doctor", nullable=False)
    clinical_criteria_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pathway: Mapped["RegionalClinicalPathway"] = relationship(
        "RegionalClinicalPathway",
        back_populates="stages",
    )
    milestones: Mapped[List["PathwayMilestone"]] = relationship(
        "PathwayMilestone",
        back_populates="stage",
        cascade="all, delete-orphan",
    )


class PathwayMilestone(Base):
    """Represents a discrete measurable milestone or clinical order required within a stage."""

    __tablename__ = "pathway_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    milestone_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    stage_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("pathway_stages.stage_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    criteria_code: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_order_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # medication, lab, imaging
    is_critical: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    stage: Mapped["PathwayStage"] = relationship(
        "PathwayStage",
        back_populates="milestones",
    )


class PatientPathwayEnrollment(Base):
    """Tracks a patient's active enrollment and execution in a regional clinical pathway."""

    __tablename__ = "patient_pathway_enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    enrollment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    pathway_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("regional_clinical_pathways.pathway_id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    facility_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    current_stage_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        index=True,
        nullable=False,
    )  # active, completed, deviated, cancelled
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_care_team_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completed_milestones: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    variance_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_variance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    pathway: Mapped["RegionalClinicalPathway"] = relationship("RegionalClinicalPathway")
    events: Mapped[List["PatientPathwayStageEvent"]] = relationship(
        "PatientPathwayStageEvent",
        back_populates="enrollment",
        cascade="all, delete-orphan",
    )


class PatientPathwayStageEvent(Base):
    """Audits stage progression, transitions, and timing metrics across facilities."""

    __tablename__ = "pathway_stage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    enrollment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("patient_pathway_enrollments.enrollment_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    stage_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    transition_type: Mapped[str] = mapped_column(String(32), nullable=False)  # start, advance, complete, variance
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    variance_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    variance_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    enrollment: Mapped["PatientPathwayEnrollment"] = relationship(
        "PatientPathwayEnrollment",
        back_populates="events",
    )
