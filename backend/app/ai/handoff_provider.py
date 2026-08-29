"""Deterministic AI Provider for Clinical Transitions of Care & Discharge Protocol Synthesis.

Phase 9.0.12: Clinical Transitions of Care, Multi-Disciplinary Handoffs (I-PASS/SBAR) & Automated Discharge Protocol Synthesis.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseHandoffDischargeProvider(ABC):
    """Abstract interface for clinical handoff and discharge protocol synthesis."""

    @abstractmethod
    def synthesize_handoff(
        self,
        framework: str,
        handoff_type: str,
        patient_name: str,
        patient_age: int,
        gender: str,
        diagnoses: list[str],
        recent_encounter_summary: Optional[str] = None,
        latest_vitals: Optional[dict[str, Any]] = None,
        active_alerts: Optional[list[dict[str, Any]]] = None,
        risk_score: Optional[float] = None,
        risk_tier: Optional[str] = None,
        custom_context: Optional[str] = None,
    ) -> dict[str, Any]:
        """Synthesize structured clinical handoff (I-PASS or SBAR)."""
        pass

    @abstractmethod
    def synthesize_discharge(
        self,
        patient_name: str,
        patient_age: int,
        gender: str,
        disposition: str,
        diagnoses: list[str],
        encounter_summary: Optional[str] = None,
        current_medications: Optional[str] = None,
        latest_vitals: Optional[dict[str, Any]] = None,
        care_plan_goals: Optional[list[str]] = None,
        risk_tier: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> dict[str, Any]:
        """Synthesize structured discharge protocol package."""
        pass


class MockHandoffDischargeProvider(BaseHandoffDischargeProvider):
    """Deterministic, 100% offline heuristic provider for clinical transitions and discharge."""

    def synthesize_handoff(
        self,
        framework: str,
        handoff_type: str,
        patient_name: str,
        patient_age: int,
        gender: str,
        diagnoses: list[str],
        recent_encounter_summary: Optional[str] = None,
        latest_vitals: Optional[dict[str, Any]] = None,
        active_alerts: Optional[list[dict[str, Any]]] = None,
        risk_score: Optional[float] = None,
        risk_tier: Optional[str] = None,
        custom_context: Optional[str] = None,
    ) -> dict[str, Any]:
        has_critical_alerts = any((a.get("severity") or "").upper() == "CRITICAL" for a in (active_alerts or []))
        high_risk = (risk_tier in ("HIGH", "CRITICAL")) or (risk_score and risk_score >= 60.0)

        # Illness Severity Classification
        if has_critical_alerts or high_risk:
            illness_severity = "unstable"
        elif active_alerts or (risk_score and risk_score >= 30.0):
            illness_severity = "watcher"
        else:
            illness_severity = "stable"

        dx_str = ", ".join(diagnoses) if diagnoses else "Active clinical monitoring"

        # Action Items
        action_items = []
        act_idx = 1
        if has_critical_alerts:
            action_items.append({
                "item_id": f"ACT-0{act_idx}",
                "task_description": "Repeat bedside vital telemetry check and verify critical alert resolution within 1 hour.",
                "role_required": "resident_or_attending",
                "priority": "STAT",
                "is_completed": False,
            })
            act_idx += 1

        action_items.append({
            "item_id": f"ACT-0{act_idx}",
            "task_description": f"Review morning lab orders and monitor fluid balance for {diagnoses[0] if diagnoses else 'underlying conditions'}.",
            "role_required": "day_shift_physician",
            "priority": "ROUTINE",
            "is_completed": False,
        })
        act_idx += 1

        action_items.append({
            "item_id": f"ACT-0{act_idx}",
            "task_description": "Verify medication administration schedule and reconcile inpatient prescriptions.",
            "role_required": "nursing_and_pharmacy",
            "priority": "ROUTINE",
            "is_completed": False,
        })

        # Situational Awareness & Contingency Plans
        contingencies = []
        contingencies.append({
            "plan_id": "CTG-01",
            "trigger_condition": "If systolic BP drops below 90 mmHg or exceeds 180 mmHg",
            "immediate_action": "Administer ordered PRN antihypertensive/IV bolus per protocol and repeat vitals in 15 minutes.",
            "escalation_contact": "On-call Hospitalist / Rapid Response Team",
        })
        contingencies.append({
            "plan_id": "CTG-02",
            "trigger_condition": "If SpO2 drops below 90% or patient exhibits acute respiratory distress",
            "immediate_action": "Initiate supplemental O2 via nasal cannula (2-4L) and order urgent portable chest X-ray and ABG.",
            "escalation_contact": "Attending Pulmonologist / Medical ICU Triage",
        })

        if framework.lower() == "sbar":
            summary = (
                f"SITUATION: {patient_name} ({patient_age}yo {gender}) undergoing {handoff_type.replace('_', ' ')} transition.\n\n"
                f"BACKGROUND: Active diagnoses include {dx_str}. "
                f"{recent_encounter_summary or 'Patient admitted for acute inpatient management.'}\n\n"
                f"ASSESSMENT: Current clinical stability classified as [{illness_severity.upper()}]. "
                f"Active risk tier is {risk_tier or 'MODERATE'} (Quantitative score: {risk_score or 45.0}/100).\n\n"
                f"RECOMMENDATION: Maintain close telemetry monitoring, execute pending care plan milestones, and adhere to defined contingency protocols."
            )
        else:  # ipass
            summary = (
                f"{patient_name} is a {patient_age}-year-old {gender} with a history of {dx_str}. "
                f"Currently transitioning via {handoff_type.replace('_', ' ')}. "
                f"{recent_encounter_summary or 'Patient remains under multi-disciplinary inpatient management.'} "
                f"Telemetry and clinical status are currently designated as [{illness_severity.upper()}]."
            )

        if custom_context:
            summary += f"\n\nAdditional Clinician Handover Notes: {custom_context}"

        return {
            "illness_severity": illness_severity,
            "summary": summary,
            "action_items": action_items,
            "situational_awareness": contingencies,
        }

    def synthesize_discharge(
        self,
        patient_name: str,
        patient_age: int,
        gender: str,
        disposition: str,
        diagnoses: list[str],
        encounter_summary: Optional[str] = None,
        current_medications: Optional[str] = None,
        latest_vitals: Optional[dict[str, Any]] = None,
        care_plan_goals: Optional[list[str]] = None,
        risk_tier: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> dict[str, Any]:
        primary_dx = diagnoses[0] if diagnoses else "Acute Medical Condition (Resolved)"
        secondary_dx = diagnoses[1:] if len(diagnoses) > 1 else ["Essential Hypertension", "Dyslipidemia"]

        hospital_course = (
            f"{patient_name}, a {patient_age}-year-old {gender}, was admitted for acute management of {primary_dx}. "
            f"During the hospital stay, diagnostic evaluations were completed, and multi-disciplinary medical therapy was optimized. "
            f"{encounter_summary or 'The patient demonstrated clinical improvement with stabilization of hemodynamics and symptom resolution.'} "
            f"The patient has met clinical discharge criteria and is ready for safe discharge with transition to {disposition.replace('_', ' ')}."
        )

        # Medication Reconciliation
        med_recon = [
            {
                "medication_name": "Lisinopril",
                "dose": "20 mg",
                "route": "oral",
                "frequency": "Once daily in the morning",
                "reconciliation_status": "continued",
                "clinical_rationale": "Blood pressure stabilization and end-organ protection.",
            },
            {
                "medication_name": "Furosemide",
                "dose": "40 mg",
                "route": "oral",
                "frequency": "Once daily with morning meal",
                "reconciliation_status": "dosage_adjusted",
                "clinical_rationale": "Decreased from inpatient 80mg IV to 40mg PO maintenance dose.",
            },
            {
                "medication_name": "Atorvastatin",
                "dose": "40 mg",
                "route": "oral",
                "frequency": "Once daily at bedtime",
                "reconciliation_status": "newly_prescribed",
                "clinical_rationale": "Initiated for secondary cardiovascular prophylaxis.",
            },
        ]

        # Follow-up appointments
        followups = [
            {
                "provider_or_specialty": "Primary Care Physician (PCP)",
                "timeframe": "7 to 10 days post-discharge",
                "purpose": "Post-discharge clinical review, vital check, and lab panel follow-up.",
                "contact_phone": "+1-800-555-CARE",
            },
            {
                "provider_or_specialty": "Cardiology Outpatient Clinic",
                "timeframe": "2 to 3 weeks post-discharge",
                "purpose": "Echocardiogram result review and heart failure medication optimization.",
                "contact_phone": "+1-800-555-CARD",
            },
        ]

        # Pending tests
        pending_tests = [
            {
                "test_name": "Blood / Sputum Culture (Final Identification & Susceptibilities)",
                "ordered_date": "Recent Inpatient Admission",
                "follow_up_physician": "Attending Hospitalist / PCP",
                "instructions": "Clinic coordinator to contact patient if pathogen sensitivities require antimicrobial adjustment.",
            }
        ]

        # Warning / Red flag symptoms
        warning_symptoms = [
            {
                "symptom_title": "Severe shortness of breath, chest pain, or sudden dizziness/syncope",
                "urgency_level": "EMERGENCY_911",
                "action_instructions": "Call 911 immediately or proceed to the nearest Emergency Department. Do NOT drive yourself.",
            },
            {
                "symptom_title": "Sudden weight gain (>3 lbs in 24 hours or >5 lbs in 1 week) or worsening leg swelling",
                "urgency_level": "URGENT_SAME_DAY",
                "action_instructions": "Contact your Cardiology or Primary Care clinic promptly for diuretic dose adjustment.",
            },
            {
                "symptom_title": "Fever (>101°F / 38.3°C), persistent nausea, or inability to take oral medications",
                "urgency_level": "CALL_CLINIC",
                "action_instructions": "Call your doctor's office within 24 hours for triage and symptom assessment.",
            },
        ]

        activity_diet = (
            "Activity: Ambulate as tolerated; avoid strenuous lifting (>10 lbs) or high-intensity exertion for 2 weeks.\n"
            "Diet: Strict low-sodium diet (<2,000 mg/day). Daily fluid restriction of 1.5 to 2.0 Liters as directed.\n"
            "Monitoring: Check and log blood pressure and body weight every morning prior to breakfast."
        )

        if custom_instructions:
            activity_diet += f"\n\nSpecial Clinician Discharge Orders: {custom_instructions}"

        return {
            "hospital_course_summary": hospital_course,
            "primary_discharge_diagnosis": primary_dx,
            "secondary_diagnoses": secondary_dx,
            "medication_reconciliation": med_recon,
            "followup_appointments": followups,
            "pending_tests": pending_tests,
            "warning_symptoms": warning_symptoms,
            "activity_and_diet_instructions": activity_diet,
        }


_provider_instance: Optional[BaseHandoffDischargeProvider] = None


def get_handoff_provider() -> BaseHandoffDischargeProvider:
    """Return singleton instance of the deterministic handoff and discharge provider."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = MockHandoffDischargeProvider()
    return _provider_instance
