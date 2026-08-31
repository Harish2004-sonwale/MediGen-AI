"""ORM Model for FHIR Bulk Data Access ($export) Asynchronous Job Tracking."""

from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class BulkExportJob(Base):
    """Tracks asynchronous population-level FHIR Bulk Data Export ($export) jobs and output URLs."""

    __tablename__ = "bulk_export_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    facility_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("clinical_facilities.facility_id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    export_type: Mapped[str] = mapped_column(String(32), default="PATIENT", nullable=False)  # PATIENT, GROUP, SYSTEM
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    output_urls_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BulkExportJob job_id={self.job_id} type={self.export_type} status={self.status}>"
