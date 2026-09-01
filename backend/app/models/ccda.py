"""SQLAlchemy ORM models for C-CDA Document Exchange & Interoperability Audit."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CCDADocumentExchange(Base):
    """Audits bidirectional C-CDA XML document exchange (import/export) across facilities."""

    __tablename__ = "ccda_document_exchanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(64),
        default="continuity_of_care_document",
        nullable=False,
    )  # continuity_of_care_document, referral_note, discharge_summary
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # export, import
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_facility: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    destination_facility: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    section_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parsed_summary_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
