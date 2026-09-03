import hashlib
import logging
from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.security import AuditAction, AuditOutcome
from app.models.user import User
from app.schemas.user import UserRole
from app.services.user_service import get_user_by_id

logger = logging.getLogger("medigen.auth.deps")

# HTTP Bearer authentication scheme
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT access token and return authenticated User model."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            user_id: Optional[int] = int(user_id_str)
        except ValueError:
            user_id = None
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check SMART access token revocation
    if payload.get("token_type") == "smart_access_token" or "client_id" in payload:
        from app.services.smart_service import smart_service
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in smart_service._revoked_token_hashes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token revoked"'},
            )

    if user_id is not None:
        user = get_user_by_id(db, user_id=user_id)
        if user is not None:
            return user

    # SMART client context fallback if user_id is not a registered DB user
    if payload.get("token_type") == "smart_access_token" or "client_id" in payload:
        return User(
            id=user_id or 1,
            email=f"{payload.get('client_id', 'smart-client')}@smart.medigen.ai",
            name=payload.get("client_id", "SMART Application"),
            role=UserRole.DOCTOR,
            is_active=True,
            default_facility_id=payload.get("facility_id", "FAC-001"),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify that current user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Please contact the hospital administrator.",
        )
    return current_user


def require_role(*allowed_roles: Any) -> Callable[[User], User]:
    """Dependency factory returning a validator that enforces user role permissions."""
    flattened_roles: list[Any] = []
    for r in allowed_roles:
        if isinstance(r, (list, tuple, set)):
            flattened_roles.extend(r)
        else:
            flattened_roles.append(r)

    def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        user_role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        allowed_vals = [r.value if hasattr(r, "value") else str(r) for r in flattened_roles]
        if current_user.role not in flattened_roles and user_role_val not in allowed_vals:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for current user role",
            )
        return current_user

    return role_checker


require_roles = require_role


def match_smart_scope(granted_scope_str: str, required_scope: str) -> bool:
    """Evaluate whether granted scope string satisfies the required SMART scope."""
    if not granted_scope_str or not required_scope:
        return False

    granted_tokens = granted_scope_str.strip().split()
    if not granted_tokens:
        return False

    # Parse required_scope: e.g. "patient/Observation.read" -> level="patient", res="Observation", action="read"
    req_parts = required_scope.split("/")
    if len(req_parts) != 2:
        return required_scope in granted_tokens
    req_level, req_res_act = req_parts[0], req_parts[1]
    req_res_parts = req_res_act.split(".")
    if len(req_res_parts) != 2:
        return required_scope in granted_tokens
    req_res, req_action = req_res_parts[0], req_res_parts[1]

    for token in granted_tokens:
        if token == required_scope:
            return True

        t_parts = token.split("/")
        if len(t_parts) != 2:
            continue
        t_level, t_res_act = t_parts[0], t_parts[1]
        t_res_parts = t_res_act.split(".")
        if len(t_res_parts) != 2:
            continue
        t_res, t_action = t_res_parts[0], t_res_parts[1]

        # Level matching: "system" or "user" covers "patient" level requests
        level_matches = (t_level == req_level) or (t_level in ("user", "system") and req_level == "patient")
        if not level_matches:
            continue

        # Resource matching: "*" covers all FHIR resource types
        res_matches = (t_res == "*") or (t_res.lower() == req_res.lower())
        if not res_matches:
            continue

        # Action matching: "*" covers all, "write" covers "write" and "read", "cruds" covers all
        action_matches = (
            (t_action == "*")
            or (t_action == req_action)
            or (t_action == "write" and req_action == "read")
            or (t_action == "cruds")
        )
        if action_matches:
            return True

    return False


def require_smart_scope(required_scope: str) -> Callable:
    """FastAPI dependency enforcing SMART on FHIR v2 fine-grained scopes.

    Preserves full access for internal clinician session JWTs.
    For SMART access tokens:
    - Validates token against revocation blacklist.
    - Evaluates granted scopes against required_scope.
    - If insufficient: emits AuditOutcome.DENIED_FORBIDDEN audit record and raises HTTP 403 Forbidden
      with error="insufficient_scope".
    """

    def scope_checker(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        db: Session = Depends(get_db),
    ) -> None:
        if credentials is None:
            return

        token = credentials.credentials
        try:
            payload = decode_access_token(token)
        except Exception:
            return

        # Determine if caller token is a SMART on FHIR token
        is_smart_token = (
            payload.get("token_type") == "smart_access_token"
            or ("client_id" in payload and "scope" in payload)
            or (
                "scope" in payload
                and any(
                    s.startswith(("patient/", "user/", "system/", "launch"))
                    for s in str(payload.get("scope", "")).split()
                )
            )
        )

        if not is_smart_token:
            return

        # Revocation check
        from app.services.smart_service import smart_service

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in smart_service._revoked_token_hashes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token revoked"'},
            )

        granted_scope = payload.get("scope", "")
        if not match_smart_scope(granted_scope, required_scope):
            client_id = payload.get("client_id", "unknown-smart-client")
            resource_type = required_scope.split("/")[1].split(".")[0] if "/" in required_scope else "FHIR"

            try:
                from app.services.audit_service import audit_service

                audit_service.emit_audit_event(
                    db=db,
                    action=AuditAction.READ,
                    resource_type=resource_type,
                    resource_id=payload.get("patient"),
                    patient_id=payload.get("patient"),
                    user_id=int(payload.get("sub")) if str(payload.get("sub", "")).isdigit() else None,
                    user_role="SMART_CLIENT",
                    purpose_of_use="TREATMENT",
                    outcome=AuditOutcome.DENIED_FORBIDDEN,
                    metadata={
                        "error": "insufficient_scope",
                        "client_id": client_id,
                        "required_scope": required_scope,
                        "granted_scope": granted_scope,
                    },
                )
            except Exception as audit_exc:
                logger.warning("Failed to emit insufficient_scope audit event: %s", audit_exc)

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient_scope",
                headers={"WWW-Authenticate": f'Bearer error="insufficient_scope", scope="{required_scope}"'},
            )

    return scope_checker
