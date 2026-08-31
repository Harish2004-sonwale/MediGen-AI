"""SQLAlchemy ORM models for Multi-Tenant Health Systems, Facilities, SMART on FHIR and Terminology."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

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
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class HealthOrganization(Base):
    """Represents a top-level healthcare provider organization or hospital network."""

    __tablename__ = "health_organizations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    org_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), index=True, nullable=False)
    org_type = Column(String(32), default="HOSPITAL_NETWORK", nullable=False)  # HOSPITAL_NETWORK, ACO, AMBULATORY_GROUP
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    facilities = relationship("ClinicalFacility", back_populates="organization", cascade="all, delete-orphan")


class ClinicalFacility(Base):
    """Represents an individual clinical hospital, ambulatory center, or clinic facility."""

    __tablename__ = "clinical_facilities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    facility_id = Column(String(64), unique=True, index=True, nullable=False)
    org_id = Column(String(64), ForeignKey("health_organizations.org_id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(128), nullable=False)
    facility_code = Column(String(32), unique=True, index=True, nullable=False)
    address_json = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    organization = relationship("HealthOrganization", back_populates="facilities")
    departments = relationship("DepartmentUnit", back_populates="facility", cascade="all, delete-orphan")
    ehr_configs = relationship("EHRIntegrationConfig", back_populates="facility", cascade="all, delete-orphan")


class DepartmentUnit(Base):
    """Represents a specialized clinical department, ward, or ICU unit within a facility."""

    __tablename__ = "department_units"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    department_id = Column(String(64), unique=True, index=True, nullable=False)
    facility_id = Column(String(64), ForeignKey("clinical_facilities.facility_id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(128), nullable=False)
    dept_code = Column(String(32), nullable=False)
    floor_or_wing = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    facility = relationship("ClinicalFacility", back_populates="departments")


class EHRIntegrationConfig(Base):
    """Represents EHR vendor connection configuration and SMART on FHIR credentials."""

    __tablename__ = "ehr_integration_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_id = Column(String(64), unique=True, index=True, nullable=False)
    facility_id = Column(String(64), ForeignKey("clinical_facilities.facility_id", ondelete="CASCADE"), index=True, nullable=False)
    ehr_vendor = Column(String(32), default="EPIC", nullable=False)  # EPIC, CERNER, ATHENAHEALTH, GENERIC_FHIR
    fhir_base_url = Column(String(255), nullable=False)
    client_id = Column(String(128), nullable=False)
    smart_auth_url = Column(String(255), nullable=True)
    smart_token_url = Column(String(255), nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    facility = relationship("ClinicalFacility", back_populates="ehr_configs")


class SmartAuthSession(Base):
    """Represents a SMART on FHIR OAuth2 authorization session and launch context."""

    __tablename__ = "smart_auth_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    client_id = Column(String(128), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    patient_id = Column(String(64), nullable=True)
    encounter_id = Column(String(64), nullable=True)
    facility_id = Column(String(64), nullable=True)
    scope = Column(String(500), nullable=False)
    code_challenge = Column(String(128), nullable=True)
    code_challenge_method = Column(String(16), default="S256", nullable=False)
    auth_code = Column(String(128), unique=True, index=True, nullable=True)
    access_token_hash = Column(String(64), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class TerminologyMapping(Base):
    """Represents a standardized clinical terminology mapping between disparate code systems."""

    __tablename__ = "terminology_mappings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mapping_id = Column(String(64), unique=True, index=True, nullable=False)
    source_system = Column(String(64), nullable=False)  # LOCAL, ICD10, PROPRIETARY
    source_code = Column(String(64), index=True, nullable=False)
    source_display = Column(String(255), nullable=False)
    target_system = Column(String(64), nullable=False)  # LOINC, SNOMED_CT, RXNORM, ICD10_CM
    target_code = Column(String(64), index=True, nullable=False)
    target_display = Column(String(255), nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
