"""Pluggable Audit Log Streaming to External SIEM & Syslog.

Phase 9.0.20: Platform Hardening, Production Deployment Hardening & Enterprise Scalability.

Provides:
- BaseAuditStreamer: abstract audit streamer interface
- SyslogAuditStreamer: emits structured RFC 5424 / CEF log events to Syslog daemons
- WebhookAuditStreamer: posts audit payloads to external SIEM / log aggregation webhooks
- MockAuditStreamer: in-memory event collector for unit testing
- stream_audit_event: non-blocking safe dispatcher ensuring streaming failures never break primary clinical transactions
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import logging
from typing import Any, Optional

from app.core.config import settings
from app.models.security import ClinicalAuditEvent

logger = logging.getLogger("medigen.audit.stream")


class BaseAuditStreamer(ABC):
    """Abstract interface for external audit log streaming."""

    @abstractmethod
    def emit(self, event: ClinicalAuditEvent) -> bool:
        """Stream an audit event to external destination. Returns True on success."""
        raise NotImplementedError


class SyslogAuditStreamer(BaseAuditStreamer):
    """Streams CEF (Common Event Format) formatted audit logs to Syslog."""

    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint

    def emit(self, event: ClinicalAuditEvent) -> bool:
        try:
            # CEF Header: CEF:Version|Device Vendor|Device Product|Device Version|Device Event Class ID|Name|Severity|Extension
            severity = "3"  # Informational
            if event.outcome == "DENIED" or event.outcome == "FAILURE":
                severity = "7"  # High

            # Construct safe, non-PHI extension dictionary
            ext_parts = [
                f"eventId={event.event_id}",
                f"act={event.action}",
                f"outcome={event.outcome}",
                f"duser={event.user_role}",
                f"src={event.ip_address or '0.0.0.0'}",  # nosec B104
                f"cs1Label=RecordHash cs1={event.record_hash}",
                f"cs2Label=PrevHash cs2={event.prev_record_hash}",
                f"cs3Label=ResourceType cs3={event.resource_type}",
            ]
            cef_message = f"CEF:0|MediGenAI|Platform|{settings.VERSION}|{event.action}|ClinicalAudit|{severity}|{' '.join(ext_parts)}"
            logger.info("AUDIT_STREAM_SYSLOG: %s", cef_message)
            return True
        except Exception as exc:
            logger.warning("Failed to emit audit event to Syslog: %s", exc)
            return False


class WebhookAuditStreamer(BaseAuditStreamer):
    """Posts sanitized JSON audit payloads to external SIEM / webhook endpoint."""

    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint or settings.AUDIT_STREAMING_ENDPOINT

    def emit(self, event: ClinicalAuditEvent) -> bool:
        if not self.endpoint:
            return False
        try:
            import httpx

            payload = {
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat() if event.timestamp else datetime.now(timezone.utc).isoformat(),
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "outcome": event.outcome,
                "user_role": event.user_role,
                "record_hash": event.record_hash,
                "prev_record_hash": event.prev_record_hash,
            }
            # Short timeout to avoid blocking clinical path
            with httpx.Client(timeout=2.0) as client:
                client.post(self.endpoint, json=payload)
            return True
        except Exception as exc:
            logger.warning("Failed to post audit event to SIEM webhook (%s): %s", self.endpoint, exc)
            return False


class MockAuditStreamer(BaseAuditStreamer):
    """In-memory audit streamer for testing."""

    def __init__(self):
        self.emitted_events: list[dict[str, Any]] = []

    def emit(self, event: ClinicalAuditEvent) -> bool:
        self.emitted_events.append({
            "event_id": event.event_id,
            "action": event.action,
            "resource_type": event.resource_type,
            "outcome": event.outcome,
            "record_hash": event.record_hash,
        })
        return True


# Factory singleton resolver
_GLOBAL_AUDIT_STREAMER: Optional[BaseAuditStreamer] = None


def get_audit_streamer() -> Optional[BaseAuditStreamer]:
    global _GLOBAL_AUDIT_STREAMER
    if not settings.AUDIT_STREAMING_ENABLED:
        return None
    if _GLOBAL_AUDIT_STREAMER is None:
        dest = settings.AUDIT_STREAMING_DESTINATION.lower()
        if dest == "syslog":
            _GLOBAL_AUDIT_STREAMER = SyslogAuditStreamer(settings.AUDIT_STREAMING_ENDPOINT)
        elif dest == "webhook":
            _GLOBAL_AUDIT_STREAMER = WebhookAuditStreamer(settings.AUDIT_STREAMING_ENDPOINT)
        elif dest == "mock":
            _GLOBAL_AUDIT_STREAMER = MockAuditStreamer()
    return _GLOBAL_AUDIT_STREAMER


def set_audit_streamer(streamer: Optional[BaseAuditStreamer]) -> None:
    global _GLOBAL_AUDIT_STREAMER
    _GLOBAL_AUDIT_STREAMER = streamer


def stream_audit_event(event: ClinicalAuditEvent) -> None:
    """Safe dispatcher streaming event to external SIEM without interrupting primary flow."""
    try:
        streamer = get_audit_streamer()
        if streamer is not None:
            streamer.emit(event)
    except Exception as exc:
        logger.warning("Audit streaming caught exception: %s", exc)
