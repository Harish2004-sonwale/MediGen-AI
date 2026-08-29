"""Clinical Risk Stratification & Predictive Scoring Engine.

Phase 9.0.11: Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification.
Provides deterministic, offline-first multi-factorial clinical risk scoring across:
- 30-day Readmission Risk
- Cardiovascular Decompensation Risk
- Clinical Deterioration / Sepsis Risk
- Medication Non-Adherence Risk
- General Mortality Risk

Zero external API keys, zero GPU, 100% offline, deterministic heuristic execution.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from app.schemas.risk_assessment import RiskFactor, RiskMitigationAction, RiskTier, RiskType


class BaseRiskStratificationProvider(ABC):
    """Abstract interface for clinical risk stratification engines."""

    @abstractmethod
    def calculate_risk(
        self,
        patient_data: dict[str, Any],
        risk_type: RiskType,
        custom_context: Optional[str] = None,
    ) -> dict[str, Any]:
        """Calculate quantitative risk score (0-100), risk tier, contributing factors, and mitigation actions."""
        raise NotImplementedError


class MockRiskStratificationProvider(BaseRiskStratificationProvider):
    """Deterministic, offline-first clinical risk scoring implementation."""

    def calculate_risk(
        self,
        patient_data: dict[str, Any],
        risk_type: RiskType,
        custom_context: Optional[str] = None,
    ) -> dict[str, Any]:
        age = patient_data.get("age", 45)
        conditions = [c.lower() for c in patient_data.get("conditions", [])]
        vitals = patient_data.get("vitals", {})
        alerts = patient_data.get("alerts", [])
        overdue_tasks = patient_data.get("overdue_tasks_count", 0)
        active_care_plans = patient_data.get("active_care_plans_count", 0)

        score = 15.0  # Baseline population risk
        factors: list[RiskFactor] = []
        mitigations: list[RiskMitigationAction] = []

        # 1. Age-based risk factor
        if age >= 75:
            score += 20.0
            factors.append(RiskFactor(
                factor_name="Geriatric Advanced Age (>=75)",
                category="demographics",
                severity="HIGH",
                observed_value=f"{age} years",
                clinical_rationale="Advanced age correlates with reduced physiological reserve and increased post-discharge vulnerability.",
            ))
        elif age >= 65:
            score += 10.0
            factors.append(RiskFactor(
                factor_name="Senior Age Bracket (65-74)",
                category="demographics",
                severity="MODERATE",
                observed_value=f"{age} years",
                clinical_rationale="Elevated baseline susceptibility for chronic disease exacerbation.",
            ))

        # 2. Comorbidity & Disease Burden
        high_risk_comorbidities = [
            ("heart failure", 25.0, "Heart Failure / Cardiomyopathy", "High risk of fluid overload and acute decompensation."),
            ("copd", 20.0, "Chronic Obstructive Pulmonary Disease", "Susceptible to acute hypoxic episodes and infectious exacerbation."),
            ("diabetes", 15.0, "Diabetes Mellitus", "Metabolic instability and micro/macrovascular complications."),
            ("hypertension", 10.0, "Essential Hypertension", "Long-term cardiovascular end-organ damage risk."),
            ("renal", 20.0, "Chronic Kidney Disease", "Impaired electrolyte excretion and drug clearance."),
        ]

        for kw, weight, name, rat in high_risk_comorbidities:
            if any(kw in c for c in conditions):
                score += weight
                factors.append(RiskFactor(
                    factor_name=name,
                    category="comorbidity",
                    severity="HIGH" if weight >= 20 else "MODERATE",
                    observed_value="Documented in Medical History",
                    clinical_rationale=rat,
                ))

        # 3. Real-time Vital Telemetry Deviations
        hr = vitals.get("heart_rate")
        sbp = vitals.get("systolic_bp")
        dbp = vitals.get("diastolic_bp")
        spo2 = vitals.get("spo2_percent")

        if hr and (hr > 100 or hr < 50):
            score += 15.0
            factors.append(RiskFactor(
                factor_name="Hemodynamic Instability: Abnormal Heart Rate",
                category="vitals",
                severity="HIGH",
                observed_value=f"{hr} bpm",
                clinical_rationale="Tachycardia or marked bradycardia indicates compensatory physiological strain or autonomic decompensation.",
            ))
            mitigations.append(RiskMitigationAction(
                action_title="12-Lead ECG & Rhythm Monitoring",
                priority="URGENT",
                suggested_task_type="diagnostic_imaging_order",
                target_timeline_days=2,
                rational="Evaluate for underlying arrhythmias, ischemia, or conduction delay.",
            ))

        if sbp and (sbp >= 160 or sbp < 90):
            score += 15.0
            factors.append(RiskFactor(
                factor_name="Severe Blood Pressure Deviation (Stage 2 / Hypotension)",
                category="vitals",
                severity="HIGH",
                observed_value=f"{sbp}/{dbp or '-'} mmHg",
                clinical_rationale="Severe hypertension increases stroke and acute cardiac afterload risk; hypotension signals hypovolemia or shock.",
            ))
            mitigations.append(RiskMitigationAction(
                action_title="Antihypertensive Titration & Daily Blood Pressure Telemetry",
                priority="URGENT",
                suggested_task_type="telemetry_check",
                target_timeline_days=3,
                rational="Prevent end-organ vascular injury through rapid pharmacological stabilization.",
            ))

        if spo2 and spo2 < 92.0:
            score += 20.0
            factors.append(RiskFactor(
                factor_name="Peripheral Hypoxemia (SpO2 < 92%)",
                category="vitals",
                severity="CRITICAL",
                observed_value=f"{spo2:.1f}%",
                clinical_rationale="Hypoxemia indicates respiratory insufficiency or ventilation-perfusion mismatch requiring immediate oxygenation evaluation.",
            ))
            mitigations.append(RiskMitigationAction(
                action_title="Pulmonary Evaluation & Arterial Blood Gas",
                priority="STAT",
                suggested_task_type="lab_test_order",
                target_timeline_days=1,
                rational="Determine severity of gas exchange impairment and rule out acute respiratory failure.",
            ))

        # 4. Clinical Alert Burden
        active_critical_alerts = sum(1 for a in alerts if a.get("severity") in ("HIGH", "CRITICAL"))
        if active_critical_alerts > 0:
            score += 15.0 * active_critical_alerts
            factors.append(RiskFactor(
                factor_name=f"Active Critical CDS Alerts ({active_critical_alerts})",
                category="alerts",
                severity="CRITICAL",
                observed_value=f"{active_critical_alerts} unacknowledged high-severity alerts",
                clinical_rationale="Unresolved critical alerts represent immediate unmitigated clinical threats.",
            ))

        # 5. Overdue Workflow Tasks & Non-Adherence
        if overdue_tasks > 0:
            score += 10.0 * min(overdue_tasks, 3)
            factors.append(RiskFactor(
                factor_name=f"Overdue Clinical Follow-up Tasks ({overdue_tasks})",
                category="adherence",
                severity="MODERATE",
                observed_value=f"{overdue_tasks} overdue tasks",
                clinical_rationale="Lapses in diagnostic orders or follow-up visits directly correlate with ambulatory care breakdown.",
            ))
            mitigations.append(RiskMitigationAction(
                action_title="Care Coordinator Outreach & Task Reconciliation",
                priority="ROUTINE",
                suggested_task_type="patient_education",
                target_timeline_days=5,
                rational="Re-engage patient to close open care gaps and schedule pending lab/consultation appointments.",
            ))

        # Protective factor: Active Care Plan in place
        if active_care_plans > 0:
            score = max(5.0, score - 10.0)
            factors.append(RiskFactor(
                factor_name="Active Structured Care Plan Enacted",
                category="protective",
                severity="LOW",
                observed_value=f"{active_care_plans} active plan(s)",
                clinical_rationale="Enacted longitudinal care plan provides structured clinical oversight and scheduled check-ins.",
            ))

        # Cap score between 0.0 and 100.0
        final_score = min(100.0, max(0.0, round(score, 1)))

        # Determine Risk Tier
        if final_score >= 75.0:
            tier = RiskTier.CRITICAL
        elif final_score >= 50.0:
            tier = RiskTier.HIGH
        elif final_score >= 25.0:
            tier = RiskTier.MODERATE
        else:
            tier = RiskTier.LOW

        # Predicted outcome narrative by risk type
        outcome_map = {
            RiskType.READMISSION_30D: f"{final_score}% estimated probability of hospital readmission within 30 days.",
            RiskType.CARDIOVASCULAR_DECOMPENSATION: f"{final_score}% risk of acute cardiovascular event or decompensated heart failure within 90 days.",
            RiskType.CLINICAL_DETERIORATION: f"{final_score}% probability of inpatient deterioration, sepsis escalation, or ICU transfer.",
            RiskType.MEDICATION_ADHERENCE: f"{final_score}% likelihood of medication non-compliance or therapy discontinuation.",
            RiskType.GENERAL_MORTALITY: f"{final_score}% 1-year multi-morbid mortality vulnerability index.",
        }
        outcome = outcome_map.get(risk_type, f"{final_score}% clinical risk index for {risk_type.value}.")

        # Default fallback mitigation if none triggered
        if not mitigations:
            mitigations.append(RiskMitigationAction(
                action_title="Routine Longitudinal Surveillance & Preventive Wellness Check",
                priority="LOW",
                suggested_task_type="followup_appointment",
                target_timeline_days=30,
                rational="Maintain stable baseline health parameters and adherence monitoring.",
            ))

        return {
            "risk_type": risk_type,
            "risk_score": final_score,
            "risk_tier": tier,
            "predicted_outcome": outcome,
            "contributing_factors": [f.model_dump(mode="json") for f in factors],
            "mitigation_recommendations": [m.model_dump(mode="json") for m in mitigations],
        }


def get_risk_provider() -> BaseRiskStratificationProvider:
    """Factory returning configured clinical risk provider."""
    return MockRiskStratificationProvider()
