"""Pydantic Schemas for FHIR R4 Topic Subscriptions and Webhook Delivery."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FHIRSubscriptionCreate(BaseModel):
    topic: str = Field(..., description="Subscription topic (e.g. patient-admit, order-created, vital-critical)")
    criteria: str = Field(..., description="FHIR criteria filter (e.g. Patient?status=active, Observation?code=883-9)")
    channel_type: str = Field(default="REST_HOOK", description="Delivery channel (REST_HOOK or WEBSOCKET)")
    endpoint_url: Optional[str] = Field(default=None, description="Target webhook receiver URL for REST_HOOK")
    secret_token: Optional[str] = Field(default=None, description="Optional bearer or HMAC secret token")
    facility_id: Optional[str] = Field(default="FAC-001", description="Tenant facility ID")


class FHIRSubscriptionUpdate(BaseModel):
    status: Optional[str] = Field(default=None, description="New status (ACTIVE, OFF, ERROR)")
    endpoint_url: Optional[str] = None
    secret_token: Optional[str] = None


class FHIRSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: str
    facility_id: Optional[str] = None
    topic: str
    criteria: str
    channel_type: str
    endpoint_url: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
