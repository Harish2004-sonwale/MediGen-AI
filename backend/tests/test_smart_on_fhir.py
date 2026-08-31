"""Unit & Integration Tests for SMART on FHIR 2.0 App Launch, PKCE and OAuth2 Tokens."""

import base64
import hashlib
import secrets
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.services.smart_service import smart_service


def test_smart_discovery_endpoints(client: TestClient):
    """Verifies standard SMART on FHIR 2.0 discovery document and JWKS."""
    # 1. Root smart-configuration
    resp = client.get("/.well-known/smart-configuration")
    assert resp.status_code == 200
    config = resp.json()
    assert "authorization_endpoint" in config
    assert "token_endpoint" in config
    assert "jwks_uri" in config
    assert "grant_types_supported" in config
    assert "authorization_code" in config["grant_types_supported"]
    assert "code_challenge_methods_supported" in config
    assert "S256" in config["code_challenge_methods_supported"]
    assert "launch/patient" in config["scopes_supported"]

    # 2. Root JWKS
    jwks_resp = client.get("/.well-known/jwks.json")
    assert jwks_resp.status_code == 200
    jwks = jwks_resp.json()
    assert "keys" in jwks
    assert len(jwks["keys"]) >= 1
    assert jwks["keys"][0]["kty"] == "RSA"
    assert jwks["keys"][0]["alg"] == "RS256"


def test_smart_oauth2_pkce_authorization_and_token_exchange(client: TestClient, db_session: Session):
    """Verifies complete SMART on FHIR 2.0 PKCE authorization and token exchange lifecycle."""
    # 1. Generate PKCE verifier and S256 challenge
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    # 2. Request Authorization Code
    auth_resp = client.get(
        "/api/v1/smart/authorize",
        params={
            "client_id": "epic-smart-client-001",
            "redirect_uri": "https://app.medigen.ai/smart/callback",
            "response_type": "code",
            "scope": "launch/patient patient/Patient.read openid fhirUser",
            "state": "random-state-1234",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "patient": "PAT-001",
            "encounter": "ENC-001",
        },
    )
    assert auth_resp.status_code == 200
    auth_data = auth_resp.json()
    assert "code" in auth_data
    auth_code = auth_data["code"]
    assert auth_data["state"] == "random-state-1234"

    # 3. Exchange Auth Code with INVALID PKCE Verifier -> Expect Failure
    bad_token_resp = client.post(
        "/api/v1/smart/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "https://app.medigen.ai/smart/callback",
            "client_id": "epic-smart-client-001",
            "code_verifier": "invalid_wrong_verifier_string_12345",
        },
    )
    assert bad_token_resp.status_code == 400
    assert "PKCE" in bad_token_resp.json()["detail"]

    # 4. Exchange Auth Code with VALID PKCE Verifier -> Expect Success
    token_resp = client.post(
        "/api/v1/smart/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "https://app.medigen.ai/smart/callback",
            "client_id": "epic-smart-client-001",
            "code_verifier": code_verifier,
        },
    )
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "Bearer"
    assert token_data["patient"] == "PAT-001"
    assert token_data["encounter"] == "ENC-001"
    assert "id_token" in token_data
    access_token = token_data["access_token"]

    # 5. Burned Code Reuse Test -> Expect Failure
    reuse_resp = client.post(
        "/api/v1/smart/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "https://app.medigen.ai/smart/callback",
            "client_id": "epic-smart-client-001",
            "code_verifier": code_verifier,
        },
    )
    assert reuse_resp.status_code == 400

    # 6. Introspect Valid Token (RFC 7662)
    introspect_resp = client.post(
        "/api/v1/smart/introspect",
        json={"token": access_token},
    )
    assert introspect_resp.status_code == 200
    intro_data = introspect_resp.json()
    assert intro_data["active"] is True
    assert intro_data["patient"] == "PAT-001"
    assert intro_data["client_id"] == "epic-smart-client-001"

    # 7. Introspect Invalid Token
    bad_intro = client.post(
        "/api/v1/smart/introspect",
        json={"token": "garbage.invalid.token.string"},
    )
    assert bad_intro.status_code == 200
    assert bad_intro.json()["active"] is False
