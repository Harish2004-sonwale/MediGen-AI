"""Deterministic AI & Rule-Based Provider for Remote Patient Monitoring, PROMs, and Telehealth.

Phase 9.0.15: Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs) & Telehealth Protocols.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Any, Optional

from app.schemas.rpm import ObservationClassification

logger = logging.getLogger("medigen.ai.rpm_provider")


class BaseRPMProvider(ABC):
    """Abstract interface for RPM observation evaluation, PROM scoring, and telehealth briefings."""

    @abstractmethod
    def evaluate_observation(
        self,
        observation_type: str,
        numeric_value: float,
        secondary_value: Optional[float] = None,
        custom_rule: Optional[Any] = None,
    ) -> tuple[str, Optional[str]]:
        """Classify observation into normal, abnormal, or critical, returning classification and reason."""
        pass

    @abstractmethod
    def score_prom(
        self,
        questions: list[dict[str, Any]],
        scoring_method: str,
        interpretation_ranges: list[dict[str, Any]],
        answers: dict[str, Any],
    ) -> tuple[float, str, list[str]]:
        """Calculate score, severity interpretation, and clinical safety flags from PROM responses."""
        pass

    @abstractmethod
    def synthesize_telehealth_briefing(
        self,
        patient_identifier: str,
        patient_name: str,
        recent_observations: list[dict[str, Any]],
        recent_prom_responses: list[dict[str, Any]],
        active_programs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Synthesize pre-visit clinical summary briefing from RPM telemetry and PROM trends."""
        pass


class MockRPMProvider(BaseRPMProvider):
    """Deterministic, 100% offline rule-based provider for clinical remote monitoring."""

    DEFAULT_THRESHOLDS = {
        "systolic_bp": {
            "normal_min": 90.0,
            "normal_max": 139.0,
            "critical_low": 80.0,
            "critical_high": 180.0,
        },
        "diastolic_bp": {
            "normal_min": 60.0,
            "normal_max": 89.0,
            "critical_low": 50.0,
            "critical_high": 120.0,
        },
        "heart_rate": {
            "normal_min": 60.0,
            "normal_max": 100.0,
            "critical_low": 45.0,
            "critical_high": 130.0,
        },
        "spo2_percent": {
            "normal_min": 95.0,
            "normal_max": 100.0,
            "critical_low": 90.0,
            "critical_high": 100.0,
        },
        "glucose_mgdl": {
            "normal_min": 70.0,
            "normal_max": 140.0,
            "critical_low": 54.0,
            "critical_high": 250.0,
        },
        "temperature_c": {
            "normal_min": 36.1,
            "normal_max": 37.5,
            "critical_low": 35.0,
            "critical_high": 39.0,
        },
        "weight_kg": {
            "normal_min": 40.0,
            "normal_max": 180.0,
            "critical_low": 35.0,
            "critical_high": 220.0,
        },
    }

    def evaluate_observation(
        self,
        observation_type: str,
        numeric_value: float,
        secondary_value: Optional[float] = None,
        custom_rule: Optional[Any] = None,
    ) -> tuple[str, Optional[str]]:
        """Evaluate observation against custom or default clinical boundaries."""
        t_cfg = self.DEFAULT_THRESHOLDS.get(observation_type.lower(), {})

        # Override with custom patient rule if provided
        normal_min = getattr(custom_rule, "normal_min", None) or t_cfg.get("normal_min")
        normal_max = getattr(custom_rule, "normal_max", None) or t_cfg.get("normal_max")
        critical_low = getattr(custom_rule, "critical_low", None) or t_cfg.get("critical_low")
        critical_high = getattr(custom_rule, "critical_high", None) or t_cfg.get("critical_high")

        # Special handling for blood pressure with secondary value (systolic + diastolic)
        if observation_type.lower() == "systolic_bp" and secondary_value is not None:
            if numeric_value >= 180.0 or secondary_value >= 120.0:
                return (
                    ObservationClassification.CRITICAL.value,
                    f"Hypertensive Crisis: BP {numeric_value}/{secondary_value} mmHg exceeds critical threshold (>=180/120).",
                )
            if numeric_value < 80.0 or secondary_value < 50.0:
                return (
                    ObservationClassification.CRITICAL.value,
                    f"Severe Hypotension: BP {numeric_value}/{secondary_value} mmHg is below critical threshold (<80/50).",
                )
            if numeric_value >= 140.0 or secondary_value >= 90.0 or numeric_value < 90.0 or secondary_value < 60.0:
                return (
                    ObservationClassification.ABNORMAL.value,
                    f"Abnormal Blood Pressure: {numeric_value}/{secondary_value} mmHg outside target range (90-139 / 60-89).",
                )
            return (ObservationClassification.NORMAL.value, None)

        # Standard single-value boundary evaluation
        if critical_high is not None and numeric_value >= critical_high:
            return (
                ObservationClassification.CRITICAL.value,
                f"Critical High: {observation_type} value ({numeric_value}) >= critical limit ({critical_high}).",
            )
        if critical_low is not None and numeric_value <= critical_low:
            return (
                ObservationClassification.CRITICAL.value,
                f"Critical Low: {observation_type} value ({numeric_value}) <= critical limit ({critical_low}).",
            )
        if (normal_max is not None and numeric_value > normal_max) or (
            normal_min is not None and numeric_value < normal_min
        ):
            return (
                ObservationClassification.ABNORMAL.value,
                f"Abnormal: {observation_type} value ({numeric_value}) outside normal range ({normal_min}-{normal_max}).",
            )

        return (ObservationClassification.NORMAL.value, None)

    def score_prom(
        self,
        questions: list[dict[str, Any]],
        scoring_method: str,
        interpretation_ranges: list[dict[str, Any]],
        answers: dict[str, Any],
    ) -> tuple[float, str, list[str]]:
        """Calculate PROM score and clinical safety flags deterministically."""
        total_score = 0.0
        safety_flags: list[str] = []

        for q in questions:
            q_id = str(q.get("id"))
            ans_val = answers.get(q_id)
            if ans_val is not None:
                try:
                    score = float(ans_val)
                    total_score += score
                    # Check for self-harm or critical safety questions (e.g. PHQ-9 Q9)
                    if (q_id == "9" or "self_harm" in q_id.lower() or "suicide" in q_id.lower()) and score > 0:
                        safety_flags.append("POSITIVE_SUICIDAL_IDEATION_FLAG: Immediate clinician review required.")
                except (ValueError, TypeError):
                    pass

        # Calculate interpretation
        interpretation = "Minimal / No Significant Symptoms"
        for r in interpretation_ranges:
            r_min = float(r.get("min", 0.0))
            r_max = float(r.get("max", 999.0))
            if r_min <= total_score <= r_max:
                interpretation = r.get("clinical_summary") or r.get("severity", "Evaluated")
                break

        return (total_score, interpretation, safety_flags)

    def synthesize_telehealth_briefing(
        self,
        patient_identifier: str,
        patient_name: str,
        recent_observations: list[dict[str, Any]],
        recent_prom_responses: list[dict[str, Any]],
        active_programs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Synthesize pre-visit clinical briefing summarizing telemetry and survey trends."""
        total_obs = len(recent_observations)
        abnormal_count = sum(
            1 for o in recent_observations if o.get("classification") in ["abnormal", "critical"]
        )
        critical_count = sum(
            1 for o in recent_observations if o.get("classification") == "critical"
        )

        compliance_rate = round(((total_obs - abnormal_count) / max(total_obs, 1)) * 100, 1)

        active_conditions = [p.get("condition_name") for p in active_programs if p.get("condition_name")]

        latest_prom_summary = None
        if recent_prom_responses:
            latest_p = recent_prom_responses[0]
            latest_prom_summary = {
                "prom_code": latest_p.get("prom_code"),
                "calculated_score": latest_p.get("calculated_score"),
                "interpretation": latest_p.get("severity_interpretation"),
                "completed_at": latest_p.get("completed_at"),
            }

        key_discussion_points = []
        if critical_count > 0:
            key_discussion_points.append(f"Review {critical_count} critical out-of-range telemetry events recorded.")
        if latest_prom_summary:
            key_discussion_points.append(
                f"Discuss latest PROM evaluation: {latest_prom_summary.get('prom_code')} score {latest_prom_summary.get('calculated_score')} ({latest_prom_summary.get('interpretation')})."
            )
        if not key_discussion_points:
            key_discussion_points.append("Review continuous RPM telemetry trends and reinforce medication adherence.")

        return {
            "patient_identifier": patient_identifier,
            "patient_name": patient_name,
            "active_programs_count": len(active_programs),
            "monitored_conditions": active_conditions,
            "telemetry_window_observations": total_obs,
            "abnormal_events_count": abnormal_count,
            "critical_events_count": critical_count,
            "telemetry_compliance_rate": compliance_rate,
            "latest_prom_summary": latest_prom_summary,
            "key_discussion_points": key_discussion_points,
            "synthesized_at": datetime.now(timezone.utc).isoformat(),
        }
