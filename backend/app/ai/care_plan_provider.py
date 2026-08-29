"""AI Care Plan Provider interface and deterministic offline implementation.

Phase 9.0.10: Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management.
Follows the same provider pattern as scribe and imaging providers.
All AI-generated care plans are strictly assistive drafts requiring clinician review.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Optional

from app.schemas.care_plan import (
    CarePlanCategory,
    CarePlanGoal,
    CarePlanIntervention,
)
from app.schemas.care_task import CareTaskType, TaskPriority

logger = logging.getLogger("medigen.ai.care_plan")


class BaseCarePlanProvider(ABC):
    """Abstract interface for clinical care plan synthesis providers."""

    @abstractmethod
    def synthesize_care_plan(
        self,
        patient_summary: dict[str, Any],
        category: CarePlanCategory,
        custom_instructions: Optional[str] = None,
    ) -> dict[str, Any]:
        """Synthesize structured clinical goals, interventions, and follow-up tasks."""
        pass


class MockCarePlanProvider(BaseCarePlanProvider):
    """Deterministic offline clinical care plan provider for development and testing.

    Requires zero external API keys, no GPU, and operates completely locally.
    """

    def synthesize_care_plan(
        self,
        patient_summary: dict[str, Any],
        category: CarePlanCategory,
        custom_instructions: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate deterministic clinical goals, interventions, and tasks based on patient context."""
        patient_name = patient_summary.get("name", "Patient")
        conditions = [str(c).lower() for c in patient_summary.get("conditions", [])]
        medications = [str(m).lower() for m in patient_summary.get("medications", [])]
        alerts = patient_summary.get("alerts", [])
        vitals = patient_summary.get("latest_vitals", {})

        now = datetime.now(timezone.utc)
        target_30d = now + timedelta(days=30)
        target_90d = now + timedelta(days=90)
        due_7d = now + timedelta(days=7)
        due_14d = now + timedelta(days=14)

        goals: list[CarePlanGoal] = []
        interventions: list[CarePlanIntervention] = []
        suggested_tasks: list[dict[str, Any]] = []

        # Domain-specific logic
        if category == CarePlanCategory.CHRONIC_DISEASE_MANAGEMENT:
            title = f"Comprehensive Chronic Disease Management Plan — {patient_name}"
            description = (
                f"Longitudinal multidisciplinary care plan for {patient_name} targeting chronic stability, "
                f"blood pressure optimization, metabolic control, and medication compliance."
            )
            goals.append(CarePlanGoal(
                goal_id="G-01",
                title="Blood Pressure Stabilization",
                target_metric="Systolic BP < 130 mmHg and Diastolic BP < 80 mmHg",
                target_date=target_90d,
                status="in_progress",
                notes="Monitor weekly averages using home telemetry log.",
            ))
            goals.append(CarePlanGoal(
                goal_id="G-02",
                title="Medication Adherence & Tolerance",
                target_metric="100% adherence with zero unmanaged adverse effects",
                target_date=target_30d,
                status="in_progress",
                notes="Review antihypertensive and lipid regimen tolerance.",
            ))
            interventions.append(CarePlanIntervention(
                intervention_id="INT-01",
                description="Home blood pressure monitoring twice daily (morning and evening).",
                category="monitoring",
                responsible_party="patient",
                status="active",
            ))
            interventions.append(CarePlanIntervention(
                intervention_id="INT-02",
                description="Dietary DASH counseling and sodium restriction (<2000mg/day).",
                category="lifestyle",
                responsible_party="dietitian",
                status="active",
            ))
            suggested_tasks.append({
                "title": "Comprehensive Metabolic Panel & Lipid Panel",
                "task_type": CareTaskType.LAB_TEST_ORDER,
                "priority": TaskPriority.ROUTINE,
                "instructions": "Fasting metabolic and renal function check.",
                "due_date": due_14d,
            })
            suggested_tasks.append({
                "title": "Clinical Follow-Up Consultation",
                "task_type": CareTaskType.FOLLOWUP_APPOINTMENT,
                "priority": TaskPriority.ROUTINE,
                "instructions": "In-person clinical evaluation for therapy titration.",
                "due_date": target_30d,
            })

        elif category == CarePlanCategory.POST_DISCHARGE_FOLLOWUP:
            title = f"Post-Discharge Transitional Care Plan — {patient_name}"
            description = (
                f"Transitional follow-up care plan for {patient_name} following recent hospital encounter. "
                f"Focuses on symptom resolution, wound/telemetry monitoring, and preventing readmission."
            )
            goals.append(CarePlanGoal(
                goal_id="G-01",
                title="Post-Hospitalization Hemodynamic Stability",
                target_metric="SpO2 >= 95% on room air, Resting HR 60-90 bpm",
                target_date=target_30d,
                status="in_progress",
                notes="Evaluate recovery baseline and exertional tolerance.",
            ))
            interventions.append(CarePlanIntervention(
                intervention_id="INT-01",
                description="Post-discharge medication reconciliation within 48-72 hours.",
                category="medical",
                responsible_party="clinical_pharmacist",
                status="active",
            ))
            suggested_tasks.append({
                "title": "Transitional Care Telemetry & Symptom Check",
                "task_type": CareTaskType.TELEMETRY_CHECK,
                "priority": TaskPriority.URGENT,
                "instructions": "Review oxygen saturation and resting vitals.",
                "due_date": due_7d,
            })
            suggested_tasks.append({
                "title": "Post-Discharge Physician Follow-Up",
                "task_type": CareTaskType.FOLLOWUP_APPOINTMENT,
                "priority": TaskPriority.ROUTINE,
                "instructions": "Evaluate clinical progress and adjust recovery directives.",
                "due_date": due_14d,
            })

        else:
            title = f"Individualized Clinical Care Plan — {patient_name}"
            description = (
                f"Personalized clinical care plan designed for {patient_name} to address current active "
                f"health priorities, preventive screenings, and clinical goals."
            )
            goals.append(CarePlanGoal(
                goal_id="G-01",
                title="Health Optimization & Risk Mitigation",
                target_metric="Annual wellness targets and guideline adherence",
                target_date=target_90d,
                status="in_progress",
            ))
            interventions.append(CarePlanIntervention(
                intervention_id="INT-01",
                description="Routine preventive care counseling and wellness assessment.",
                category="education",
                responsible_party="clinician",
                status="active",
            ))
            suggested_tasks.append({
                "title": "Preventive Care Review",
                "task_type": CareTaskType.PATIENT_EDUCATION,
                "priority": TaskPriority.ROUTINE,
                "instructions": "Provide lifestyle and preventive health documentation.",
                "due_date": due_14d,
            })

        if custom_instructions:
            description += f"\n\n[CLINICIAN FOCUS DIRECTIVE]: {custom_instructions.strip()}"

        return {
            "title": title,
            "category": category,
            "description": description,
            "goals": [g.model_dump(mode="json") for g in goals],
            "interventions": [i.model_dump(mode="json") for i in interventions],
            "suggested_tasks": suggested_tasks,
            "is_ai_generated": True,
            "start_date": now,
            "end_date": target_90d,
        }


def get_care_plan_provider() -> BaseCarePlanProvider:
    """Factory returning configured care plan synthesis provider."""
    return MockCarePlanProvider()
