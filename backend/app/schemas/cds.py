"""Pydantic schemas for CDS Hooks Specification v2.0 and CDS Cards."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CDSService(BaseModel):
    """Definition of an exposed CDS Service for discovery."""

    hook: str = Field(..., description="Hook name, e.g. patient-view, order-select, order-sign")
    name: str = Field(..., description="Unique machine-readable service identifier")
    id: str = Field(..., description="Unique service ID matching name")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Clinical purpose of the CDS service")
    prefetch: Optional[Dict[str, str]] = Field(default_factory=dict, description="FHIR read queries to prefetch")
    usageRequirements: Optional[str] = None


class CDSServicesDiscoveryResponse(BaseModel):
    """Response returned by GET /cds-services."""

    services: List[CDSService]


class CDSHookContext(BaseModel):
    """Context object specific to the CDS hook type."""

    userId: Optional[str] = None
    patientId: Optional[str] = None
    encounterId: Optional[str] = None
    selections: Optional[List[str]] = None
    draftOrders: Optional[Dict[str, Any]] = None
    appointments: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = "allow"


class CDSHookRequest(BaseModel):
    """Payload sent by EHR to invoke a CDS Hook."""

    hook: str
    hookInstance: str
    fhirServer: Optional[str] = None
    fhirAuthorization: Optional[Dict[str, Any]] = None
    user: Optional[str] = None
    context: CDSHookContext
    prefetch: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CDSSource(BaseModel):
    """Source provenance for a CDS Card."""

    label: str
    url: Optional[str] = None
    icon: Optional[str] = None
    topic: Optional[Dict[str, Any]] = None


class CDSSuggestionAction(BaseModel):
    """Suggested structured action to modify EHR resources."""

    type: str = Field(..., description="create, update, delete")
    description: str
    resource: Optional[Dict[str, Any]] = None


class CDSSuggestion(BaseModel):
    """Actionable recommendation inside a CDS Card."""

    label: str
    uuid: Optional[str] = None
    isRecommended: Optional[bool] = False
    actions: List[CDSSuggestionAction] = []


class CDSLink(BaseModel):
    """Link to external guidelines or SMART App launch."""

    label: str
    url: str
    type: str = Field(default="absolute", description="smart or absolute")
    appContext: Optional[str] = None


class CDSCard(BaseModel):
    """Standardized CDS Hooks Card."""

    uuid: Optional[str] = None
    summary: str = Field(..., description="Brief one-line summary (max 140 chars)")
    detail: Optional[str] = Field(None, description="Detailed clinical guidance in Markdown")
    indicator: str = Field(..., description="info, warning, critical")
    source: CDSSource
    suggestions: List[CDSSuggestion] = []
    selectionBehavior: Optional[str] = "at-most-one"
    overrideReasons: Optional[List[Dict[str, str]]] = None
    links: List[CDSLink] = []


class CDSHookResponse(BaseModel):
    """Response containing CDS decision support cards."""

    cards: List[CDSCard] = []
