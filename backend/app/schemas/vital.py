"""Pydantic schemas for Vital Telemetry Ingestion, Validation & Simulation.

Phase 9.0.9: Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class VitalSimulationProfile(str, Enum):
    """Preset physiological simulation profiles."""

    NORMAL = "normal"
    HYPOXIC = "hypoxic"
    HYPERTENSIVE_CRISIS = "hypertensive_crisis"
    TACHYCARDIC = "tachycardic"
    BRADYCARDIC = "bradycardic"


class VitalTelemetryCreate(BaseModel):
    """Payload for ingesting structured patient vital telemetry."""

    heart_rate: Optional[int] = Field(
        default=None,
        ge=20,
        le=300,
        description="Heart rate in beats per minute (bpm)",
    )
    systolic_bp: Optional[int] = Field(
        default=None,
        ge=30,
        le=300,
        description="Systolic blood pressure in mmHg",
    )
    diastolic_bp: Optional[int] = Field(
        default=None,
        ge=20,
        le=200,
        description="Diastolic blood pressure in mmHg",
    )
    respiratory_rate: Optional[int] = Field(
        default=None,
        ge=4,
        le=60,
        description="Respiratory rate in breaths per minute",
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=20.0,
        le=115.0,
        description="Body temperature in Celsius or Fahrenheit (auto-normalized to Celsius)",
    )
    spo2_percent: Optional[float] = Field(
        default=None,
        ge=50.0,
        le=100.0,
        description="Blood oxygen saturation percentage (SpO2)",
    )
    weight_kg: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=500.0,
        description="Body weight in kilograms",
    )
    device_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Originating bedside monitor or telemetry device identifier",
    )
    source: str = Field(
        default="manual_entry",
        max_length=50,
        description="Source channel (e.g. 'bedside_monitor', 'simulator', 'manual_entry')",
    )
    measured_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when telemetry was measured (defaults to current time)",
    )

    @field_validator("temperature")
    @classmethod
    def normalize_temperature(cls, v: Optional[float]) -> Optional[float]:
        """Normalize Fahrenheit to Celsius if value is above standard Celsius physiologic limits."""
        if v is None:
            return None
        if v > 45.0:
            # Assume Fahrenheit: (F - 32) * 5 / 9
            celsius = (v - 32.0) * (5.0 / 9.0)
            return round(celsius, 2)
        return round(v, 2)


class VitalSimulateRequest(BaseModel):
    """Payload to trigger simulated telemetry ingestion for testing/demo."""

    profile: VitalSimulationProfile = Field(
        default=VitalSimulationProfile.NORMAL,
        description="Physiological simulation pattern",
    )
    device_id: Optional[str] = Field(
        default="telemetry_sim_01",
        max_length=64,
    )


class VitalTelemetryResponse(BaseModel):
    """Full representation of a recorded vital telemetry reading."""

    id: int
    reading_id: str
    patient_id: int
    encounter_id: Optional[int]
    heart_rate: Optional[int]
    systolic_bp: Optional[int]
    diastolic_bp: Optional[int]
    respiratory_rate: Optional[int]
    temperature_c: Optional[float]
    spo2_percent: Optional[float]
    weight_kg: Optional[float]
    device_id: Optional[str]
    source: str
    measured_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VitalTelemetryListResponse(BaseModel):
    """List response envelope for historical vital telemetry."""

    items: list[VitalTelemetryResponse]
    total: int
