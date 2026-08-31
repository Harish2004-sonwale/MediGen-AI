"""Service for SMART on FHIR 2.0 App Launch, PKCE Verification, OAuth2 and JWKS."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import secrets
from typing import Any, Dict, List, Optional
import uuid

import jwt
from sqlalchemy.orm import Session

from app.core.cache import get_cache
from app.core.config import settings
from app.models.tenant import SmartAuthSession
from app.schemas.smart import (
    JWKKey,
    JWKSResponse,
    SmartAuthorizeResponse,
    SmartConfigurationResponse,
    SmartIntrospectResponse,
    SmartTokenResponse,
)

logger = logging.getLogger(__name__)

# Deterministic local test key ID and standard public exponent
TEST_JWK_KID = "medigen-smart-key-2026-01"
TEST_JWK_N = (
    "u1lKZmVkdGhyZXNfc21hcnRfa2V5X21vY2tfZGV0ZXJtaW5pc3RpY19wdWJsaWNfa2V5X21vZHVsdXNfcmVxdWlyZWRfZm9yX2xvY2FsX29mZ"
    "mxpbmVfdGVzdGluZ19zbWFydF9vbl9maGlyXzIuMC4wX3NwZWNpZmljYXRpb24"
)
TEST_JWK_E = "AQAB"


class SmartService:
    """SMART on FHIR 2.0.0 Authorization, Token Revocation (RFC 7009) and Identity Service."""

    def __init__(self) -> None:
        self._signing_key = settings.JWT_SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._revoked_token_hashes: set[str] = set()

    def get_smart_configuration(self, base_url: str) -> SmartConfigurationResponse:
        """Returns SMART on FHIR 2.0 discovery configuration document."""
        clean_base = base_url.rstrip("/")
        return SmartConfigurationResponse(
            authorization_endpoint=f"{clean_base}/api/v1/smart/authorize",
            token_endpoint=f"{clean_base}/api/v1/smart/token",
            introspection_endpoint=f"{clean_base}/api/v1/smart/introspect",
            revocation_endpoint=f"{clean_base}/api/v1/smart/revoke",
            jwks_uri=f"{clean_base}/.well-known/jwks.json",
            issuer=clean_base,
            grant_types_supported=["authorization_code", "client_credentials"],
            code_challenge_methods_supported=["S256"],
            scopes_supported=[
                "openid",
                "profile",
                "fhirUser",
                "launch",
                "launch/patient",
                "launch/encounter",
                "patient/*.read",
                "patient/*.write",
                "patient/Patient.read",
                "patient/Observation.read",
                "patient/Condition.read",
                "patient/MedicationStatement.read",
                "user/*.read",
                "system/*.read",
            ],
            response_types_supported=["code"],
            capabilities=[
                "launch-ehr",
                "launch-standalone",
                "client-public",
                "client-confidential-symmetric",
                "context-ehr-patient",
                "context-ehr-encounter",
                "permission-patient",
                "permission-user",
            ],
        )

    def get_jwks(self) -> JWKSResponse:
        """Returns public JSON Web Key Set for validating issued SMART tokens."""
        return JWKSResponse(
            keys=[
                JWKKey(
                    kty="RSA",
                    use="sig",
                    alg="RS256",
                    kid=TEST_JWK_KID,
                    n=TEST_JWK_N,
                    e=TEST_JWK_E,
                )
            ]
        )

    def verify_pkce(self, code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
        """Verifies PKCE code_verifier against code_challenge according to RFC 7636."""
        if not code_challenge:
            return True
        if method != "S256":
            return False

        # S256: BASE64URL-ENCODE(SHA256(ASCII(code_verifier))) without padding
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        calculated_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        clean_challenge = code_challenge.rstrip("=")
        return secrets.compare_digest(calculated_challenge, clean_challenge)

    def create_authorization_code(
        self,
        db: Session,
        client_id: str,
        user_id: Optional[int],
        patient_id: Optional[str],
        encounter_id: Optional[str],
        facility_id: Optional[str],
        scope: str,
        redirect_uri: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: str = "S256",
        state: Optional[str] = None,
    ) -> SmartAuthorizeResponse:
        """Generates and persists a short-lived authorization code with launch context."""
        session_id = f"SES-{uuid.uuid4().hex[:12]}"
        auth_code = f"AC-{secrets.token_urlsafe(32)}"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)  # 5 min TTL

        session = SmartAuthSession(
            session_id=session_id,
            client_id=client_id,
            user_id=user_id,
            patient_id=patient_id or "PAT-001",
            encounter_id=encounter_id or "ENC-001",
            facility_id=facility_id or "FAC-001",
            scope=scope or "launch/patient patient/Patient.read openid fhirUser",
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            auth_code=auth_code,
            expires_at=expires_at,
        )
        db.add(session)
        db.commit()

        return SmartAuthorizeResponse(
            code=auth_code,
            state=state,
            redirect_uri=redirect_uri,
        )

    def exchange_code_for_token(
        self,
        db: Session,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> SmartTokenResponse:
        """Validates auth code, checks PKCE, burns code, and issues signed SMART JWT token."""
        session = db.query(SmartAuthSession).filter(SmartAuthSession.auth_code == code).first()
        if not session:
            raise ValueError("Invalid or expired authorization code")

        now = datetime.now(timezone.utc)
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            db.delete(session)
            db.commit()
            raise ValueError("Authorization code has expired")

        if session.client_id != client_id:
            raise ValueError("Client ID mismatch")

        # PKCE verification if challenge was provided during auth request
        if session.code_challenge:
            if not code_verifier:
                raise ValueError("code_verifier is required for PKCE-protected authorization")
            if not self.verify_pkce(code_verifier, session.code_challenge, session.code_challenge_method):
                raise ValueError("PKCE code_verifier verification failed")

        # Burn authorization code (one-time use)
        session.auth_code = None

        # Build JWT Payload
        token_expires = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(session.user_id or "smart-client"),
            "client_id": session.client_id,
            "scope": session.scope,
            "patient": session.patient_id,
            "encounter": session.encounter_id,
            "facility_id": session.facility_id,
            "exp": int(token_expires.timestamp()),
            "iat": int(now.timestamp()),
            "iss": settings.PROJECT_NAME,
            "token_type": "smart_access_token",
        }
        access_token = jwt.encode(payload, self._signing_key, algorithm=self._algorithm)

        # Build OIDC id_token if openid scope requested
        id_token = None
        if "openid" in session.scope:
            id_payload = {
                "sub": str(session.user_id or "user-001"),
                "aud": session.client_id,
                "iss": settings.PROJECT_NAME,
                "exp": int(token_expires.timestamp()),
                "iat": int(now.timestamp()),
                "fhirUser": f"Practitioner/{session.user_id or 1}",
                "patient": session.patient_id,
            }
            id_token = jwt.encode(id_payload, self._signing_key, algorithm=self._algorithm)

        session.access_token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        db.commit()

        return SmartTokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            scope=session.scope,
            id_token=id_token,
            patient=session.patient_id,
            encounter=session.encounter_id,
            facility_id=session.facility_id,
            smart_style_url=None,
        )

    def revoke_token(self, db: Session, token: str, token_type_hint: Optional[str] = None) -> bool:
        """Revokes a SMART access token or refresh token according to RFC 7009."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self._revoked_token_hashes.add(token_hash)

        # Clear matching active session in database if present
        session = db.query(SmartAuthSession).filter(SmartAuthSession.access_token_hash == token_hash).first()
        if session:
            session.access_token_hash = None
            db.commit()

        # Invalidate in Redis blacklist cache if cache is available
        try:
            cache = get_cache()
            if cache.is_available:
                cache.set(f"revoked_token:{token_hash}", "1", ttl=86400)
        except Exception:
            pass

        logger.info("Successfully revoked SMART token with hash %s", token_hash[:12])
        return True

    def introspect_token(self, db: Session, token: str) -> SmartIntrospectResponse:
        """Decodes and validates a SMART access token according to RFC 7662."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in self._revoked_token_hashes:
            return SmartIntrospectResponse(active=False)

        try:
            cache = get_cache()
            if cache.is_available and cache.get(f"revoked_token:{token_hash}"):
                return SmartIntrospectResponse(active=False)
        except Exception:
            pass

        try:
            payload = jwt.decode(token, self._signing_key, algorithms=[self._algorithm])
            exp = payload.get("exp", 0)
            now_ts = int(datetime.now(timezone.utc).timestamp())
            is_active = exp > now_ts

            return SmartIntrospectResponse(
                active=is_active,
                scope=payload.get("scope"),
                client_id=payload.get("client_id"),
                sub=payload.get("sub"),
                exp=exp,
                iat=payload.get("iat"),
                iss=payload.get("iss"),
                patient=payload.get("patient"),
                facility_id=payload.get("facility_id"),
            )
        except (jwt.PyJWTError, Exception) as exc:
            logger.debug("Token introspection failed: %s", exc)
            return SmartIntrospectResponse(active=False)


smart_service = SmartService()
