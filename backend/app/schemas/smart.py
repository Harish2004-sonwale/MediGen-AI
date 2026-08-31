"""Pydantic schemas for SMART on FHIR 2.0 App Launch, OAuth2 and JWKS."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SmartConfigurationResponse(BaseModel):
    """SMART on FHIR 2.0 capabilities discovery manifest."""

    authorization_endpoint: str
    token_endpoint: str
    introspection_endpoint: Optional[str] = None
    management_endpoint: Optional[str] = None
    revocation_endpoint: Optional[str] = None
    jwks_uri: str
    issuer: Optional[str] = None
    grant_types_supported: List[str] = ["authorization_code", "client_credentials"]
    code_challenge_methods_supported: List[str] = ["S256"]
    scopes_supported: List[str] = [
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
    ]
    response_types_supported: List[str] = ["code"]
    capabilities: List[str] = [
        "launch-ehr",
        "launch-standalone",
        "client-public",
        "client-confidential-symmetric",
        "context-ehr-patient",
        "context-ehr-encounter",
        "permission-patient",
        "permission-user",
    ]


class JWKKey(BaseModel):
    kty: str = "RSA"
    use: str = "sig"
    alg: str = "RS256"
    kid: str
    n: str
    e: str


class JWKSResponse(BaseModel):
    keys: List[JWKKey]


class SmartAuthorizeResponse(BaseModel):
    code: str
    state: Optional[str] = None
    redirect_uri: str


class SmartTokenRequest(BaseModel):
    grant_type: str = "authorization_code"
    code: str
    redirect_uri: str
    client_id: str
    code_verifier: Optional[str] = None


class SmartTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 900
    scope: str
    id_token: Optional[str] = None
    patient: Optional[str] = None
    encounter: Optional[str] = None
    facility_id: Optional[str] = None
    smart_style_url: Optional[str] = None


class SmartIntrospectRequest(BaseModel):
    token: str
    token_type_hint: Optional[str] = "access_token"


class SmartIntrospectResponse(BaseModel):
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    sub: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    iss: Optional[str] = None
    patient: Optional[str] = None
    facility_id: Optional[str] = None


class SmartRevokeRequest(BaseModel):
    token: str
    token_type_hint: Optional[str] = "access_token"


class SmartRevokeResponse(BaseModel):
    revoked: bool
    message: str
