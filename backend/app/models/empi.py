"""SQLAlchemy ORM models for Federated Enterprise Master Patient Index (EMPI)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class EnterprisePatientIdentity(Base):
    """Represents a global Enterprise Master Patient Index (EMPI) Golden Record identity."""

    __tablename__ = "enterprise_patient_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    enterprise_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="TENANT-001")
    primary_patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active, merged, split
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
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

    # Relationships
    links: Mapped[List["PatientIdentityLink"]] = relationship(
        "PatientIdentityLink",
        back_populates="enterprise_identity",
        cascade="all, delete-orphan",
    )


class PatientIdentityLink(Base):
    """Maps a facility-scoped local Patient record to an Enterprise Master Patient Record."""

    __tablename__ = "patient_identity_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    enterprise_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("enterprise_patient_identities.enterprise_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    link_type: Mapped[str] = mapped_column(
        String(32),
        default="deterministic_exact",
        nullable=False,
    )  # deterministic_exact, probabilistic_auto, manual_merge
    match_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    enterprise_identity: Mapped["EnterprisePatientIdentity"] = relationship(
        "EnterprisePatientIdentity",
        back_populates="links",
    )


class EMPIMatchReview(Base):
    """Represents a candidate identity match flagged for manual HIM/Registrar review."""

    __tablename__ = "empi_match_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    review_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id_a: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    patient_id_b: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    facility_id_a: Mapped[str] = mapped_column(String(64), nullable=False)
    facility_id_b: Mapped[str] = mapped_column(String(64), nullable=False)
    enterprise_id_a: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    enterprise_id_b: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    feature_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending_review",
        index=True,
        nullable=False,
    )  # pending_review, approved_linked, approved_merged, rejected_distinct
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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


class EMPIMergeHistory(Base):
    """Tracks merge and split audit lineage across enterprise patient identities."""

    __tablename__ = "empi_merge_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    merge_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    target_enterprise_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_enterprise_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    merged_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    merge_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    is_reverted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reverted_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reverted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
