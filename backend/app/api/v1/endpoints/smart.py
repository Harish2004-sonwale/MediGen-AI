"""API Endpoints for SMART on FHIR 2.0 App Launch, OAuth2 and JWKS Discovery."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.smart import (
    JWKSResponse,
    SmartAuthorizeResponse,
    SmartConfigurationResponse,
    SmartIntrospectRequest,
    SmartIntrospectResponse,
    SmartRevokeRequest,
    SmartRevokeResponse,
    SmartTokenRequest,
    SmartTokenResponse,
)
from app.services.smart_service import smart_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/smart-configuration", response_model=SmartConfigurationResponse, summary="SMART on FHIR Discovery")
def get_smart_configuration(request: Request) -> SmartConfigurationResponse:
    """Returns SMART on FHIR 2.0 capability discovery document."""
    base_url = str(request.base_url).rstrip("/")
    return smart_service.get_smart_configuration(base_url)


@router.get("/jwks.json", response_model=JWKSResponse, summary="Public JSON Web Key Set")
def get_jwks() -> JWKSResponse:
    """Returns public key set for verifying SMART access and ID tokens."""
    return smart_service.get_jwks()


@router.get("/authorize", response_model=SmartAuthorizeResponse, summary="SMART OAuth2 Authorization Endpoint")
def smart_authorize(
    client_id: str = Query(..., description="Registered OAuth2 client ID"),
    redirect_uri: str = Query(..., description="Client redirect URI"),
    response_type: str = Query("code", description="Must be 'code'"),
    scope: str = Query("launch/patient patient/Patient.read openid fhirUser", description="OAuth2 scopes"),
    state: Optional[str] = Query(None, description="Client state token"),
    code_challenge: Optional[str] = Query(None, description="PKCE code challenge"),
    code_challenge_method: Optional[str] = Query("S256", description="PKCE method (S256)"),
    launch: Optional[str] = Query(None, description="EHR launch identifier"),
    patient: Optional[str] = Query(None, description="Explicit patient launch context"),
    encounter: Optional[str] = Query(None, description="Explicit encounter launch context"),
    facility_id: Optional[str] = Query("FAC-001", description="Tenant facility context"),
    db: Session = Depends(get_db),
) -> SmartAuthorizeResponse:
    """Issues an authorization code containing the requested launch context and scopes."""
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported response_type. Must be 'code'.",
        )

    patient_context = patient or (f"PAT-{launch[:6]}" if launch else "PAT-001")

    return smart_service.create_authorization_code(
        db=db,
        client_id=client_id,
        user_id=1,
        patient_id=patient_context,
        encounter_id=encounter or "ENC-001",
        facility_id=facility_id or "FAC-001",
        scope=scope,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method or "S256",
        state=state,
    )


@router.post("/token", response_model=SmartTokenResponse, summary="SMART OAuth2 Token Exchange Endpoint")
def smart_token(
    grant_type: str = Form("authorization_code"),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    code_verifier: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> SmartTokenResponse:
    """Exchanges an authorization code and PKCE code_verifier for a SMART access token."""
    if grant_type != "authorization_code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant_type. Must be 'authorization_code'.",
        )

    try:
        return smart_service.exchange_code_for_token(
            db=db,
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/introspect", response_model=SmartIntrospectResponse, summary="SMART Token Introspection")
def smart_introspect(
    payload: SmartIntrospectRequest,
    db: Session = Depends(get_db),
) -> SmartIntrospectResponse:
    """Validates and introspects a SMART access token (RFC 7662)."""
    return smart_service.introspect_token(db=db, token=payload.token)


@router.post("/revoke", response_model=SmartRevokeResponse, summary="SMART Token Revocation")
def smart_revoke(
    payload: SmartRevokeRequest,
    db: Session = Depends(get_db),
) -> SmartRevokeResponse:
    """Revokes a SMART access or refresh token (RFC 7009)."""
    revoked = smart_service.revoke_token(
        db=db,
        token=payload.token,
        token_type_hint=payload.token_type_hint,
    )
    return SmartRevokeResponse(
        revoked=revoked,
        message="Token revocation processed successfully.",
    )
