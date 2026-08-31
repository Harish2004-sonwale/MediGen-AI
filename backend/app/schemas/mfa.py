"""Pydantic Schemas for Multi-Factor Authentication (TOTP RFC 6238)."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    backup_codes: List[str]
    message: str


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=16, description="6-digit TOTP code or 8-character backup recovery code")


class MFAVerifyResponse(BaseModel):
    verified: bool
    message: str


class MFAStatusResponse(BaseModel):
    is_enabled: bool
    backup_codes_remaining: int
    last_used_at: Optional[datetime] = None
