"""ORM Model for HL7 FHIR R4 Topic and REST-hook Subscriptions."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FHIRSubscription(Base):
    """Tracks active FHIR R4 topic subscriptions and endpoint delivery channels."""

    __tablename__ = "fhir_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    subscription_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    facility_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("clinical_facilities.facility_id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    topic: Mapped[str] = mapped_column(String(128), index=True, nullable=False)  # patient-admit, encounter-close, order-created, vital-critical
    criteria: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(32), default="REST_HOOK", nullable=False)  # REST_HOOK, WEBSOCKET
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    secret_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="REQUESTED", index=True, nullable=False)  # REQUESTED, ACTIVE, OFF, ERROR
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<FHIRSubscription sub_id={self.subscription_id} topic={self.topic} status={self.status}>"
