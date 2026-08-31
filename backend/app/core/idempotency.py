"""Idempotency and Request Deduplication Engine for Clinical Mutations."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Optional
from fastapi import HTTPException, Header, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyRecord


def compute_request_hash(payload: Any) -> str:
    """Compute deterministic SHA-256 hash of serialized JSON payload."""
    if isinstance(payload, bytes):
        raw = payload
    elif isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def check_and_get_cached_idempotency_response(
    db: Session,
    idempotency_key: str,
    endpoint: str,
    request_payload: Any,
) -> Optional[tuple[int, dict[str, Any]]]:
    """Check if an identical request was already processed under this idempotency key.

    Returns (status_code, body_json) if cached match, raises 422 if payload mismatch, or returns None.
    """
    req_hash = compute_request_hash(request_payload)
    stmt = select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == idempotency_key)
    record = db.execute(stmt).scalars().first()

    if record is None:
        return None

    # Check expiration
    now = datetime.now(timezone.utc)
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        # Expired record, delete and allow re-execution
        db.delete(record)
        db.commit()
        return None

    # Payload hash comparison
    if record.request_hash != req_hash:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Idempotency key '{idempotency_key}' was previously used with a different request payload. "
                "Provide a new idempotency key for distinct clinical mutations."
            ),
        )

    try:
        body = json.loads(record.response_body)
    except Exception:
        body = {"raw": record.response_body}

    return record.response_code, body


def store_idempotency_response(
    db: Session,
    idempotency_key: str,
    endpoint: str,
    request_payload: Any,
    response_code: int,
    response_body: Any,
    user_id: Optional[int] = None,
    facility_id: Optional[str] = None,
    ttl_hours: int = 24,
) -> IdempotencyRecord:
    """Store the completed mutation response to serve subsequent retried requests."""
    req_hash = compute_request_hash(request_payload)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)

    body_str = (
        response_body
        if isinstance(response_body, str)
        else json.dumps(response_body, default=str)
    )

    record = IdempotencyRecord(
        idempotency_key=idempotency_key,
        endpoint=endpoint,
        user_id=user_id,
        facility_id=facility_id or "FAC-001",
        request_hash=req_hash,
        response_code=response_code,
        response_body=body_str,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
