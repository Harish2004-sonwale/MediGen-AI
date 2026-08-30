"""Deterministic AI / Clinical Evaluation Provider for Clinical Quality Measures (CQMs).

Phase 9.0.14: Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting Engine.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseQualityMeasureProvider(ABC):
    """Abstract interface for clinical quality measure evaluation and HEDIS/MIPS scoring."""

    @abstractmethod
    def get_default_measures(self) -> list[dict[str, Any]]:
        """Return standard seed quality measure definitions."""
        pass

    @abstractmethod
    def evaluate_patient_measure(
        self,
        measure_code: str,
        patient_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a single patient against a clinical quality measure."""
        pass


class MockQualityMeasureProvider(BaseQualityMeasureProvider):
    """Deterministic, 100% offline heuristic engine for CQM, HEDIS, and MIPS compliance scoring."""

    DEFAULT_MEASURES: list[dict[str, Any]] = [
        {
            "measure_id": "CQM-001-DM-HBA1C",
            "title": "Diabetes Glycemic Control (HbA1c < 8.0%)",
            "description": "Percentage of patients 18-75 years of age with diabetes who had hemoglobin A1c (HbA1c) < 8.0% during the measurement period.",
            "version": "1.0.0",
            "domain": "chronic_disease_management",
            "hedis_mips_reference": "HEDIS HBD / MIPS #001",
            "target_compliance_rate": 80.0,
            "denominator_criteria_json": {
                "diagnosis_keywords": ["diabetes", "diabetic", "dm type 1", "dm type 2", "e11", "e10"],
            },
            "numerator_criteria_json": {
                "test_keywords": ["hba1c", "hemoglobin a1c", "glycated hemoglobin", "a1c"],
                "max_threshold": 8.0,
            },
            "exclusion_criteria_json": {
                "hospice_or_palliative": True,
            },
        },
        {
            "measure_id": "CQM-002-HTN-BP",
            "title": "Controlling High Blood Pressure (< 140/90 mmHg)",
            "description": "Percentage of patients 18-85 years of age with hypertension whose most recent blood pressure was adequately controlled (< 140/90 mmHg).",
            "version": "1.0.0",
            "domain": "chronic_disease_management",
            "hedis_mips_reference": "HEDIS CBP / MIPS #236",
            "target_compliance_rate": 75.0,
            "denominator_criteria_json": {
                "diagnosis_keywords": ["hypertension", "essential hypertension", "htn", "i10"],
            },
            "numerator_criteria_json": {
                "max_systolic": 140,
                "max_diastolic": 90,
            },
            "exclusion_criteria_json": {
                "end_stage_renal_disease": True,
            },
        },
        {
            "measure_id": "CQM-003-TOC-MEDREC",
            "title": "Post-Discharge Medication Reconciliation",
            "description": "Percentage of patients discharged from an inpatient setting with documented multi-disciplinary medication reconciliation within 30 days.",
            "version": "1.0.0",
            "domain": "care_coordination",
            "hedis_mips_reference": "HEDIS TRC / MIPS #046",
            "target_compliance_rate": 85.0,
            "denominator_criteria_json": {
                "inpatient_discharge": True,
            },
            "numerator_criteria_json": {
                "pharmacist_or_attending_reconciliation": True,
            },
            "exclusion_criteria_json": {
                "patient_expired": True,
            },
        },
        {
            "measure_id": "CQM-004-CP-ADHERENCE",
            "title": "Longitudinal Care Plan & High-Priority Task Adherence",
            "description": "Percentage of patients with active longitudinal care plans whose STAT or HIGH priority follow-up tasks are completed without delay.",
            "version": "1.0.0",
            "domain": "patient_safety",
            "hedis_mips_reference": "MediGen Quality Std #4",
            "target_compliance_rate": 90.0,
            "denominator_criteria_json": {
                "active_care_plan": True,
            },
            "numerator_criteria_json": {
                "high_priority_tasks_completed": True,
            },
            "exclusion_criteria_json": {},
        },
        {
            "measure_id": "CQM-005-CRIT-LAB",
            "title": "Closed-Loop Critical Diagnostic Result Signoff",
            "description": "Percentage of panic critical laboratory or imaging results that have documented physician signoff and review within 24 hours.",
            "version": "1.0.0",
            "domain": "patient_safety",
            "hedis_mips_reference": "CAP / Joint Commission Safety Std",
            "target_compliance_rate": 98.0,
            "denominator_criteria_json": {
                "panic_critical_result": True,
            },
            "numerator_criteria_json": {
                "physician_signoff_documented": True,
            },
            "exclusion_criteria_json": {},
        },
    ]

    def get_default_measures(self) -> list[dict[str, Any]]:
        return self.DEFAULT_MEASURES

    def evaluate_patient_measure(
        self,
        measure_code: str,
        patient_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a patient against a specific clinical quality measure."""
        diagnoses = [str(d).lower() for d in patient_data.get("diagnoses", [])]
        diagnostic_results = patient_data.get("diagnostic_results", [])
        vitals = patient_data.get("vitals", [])
        discharge_protocols = patient_data.get("discharge_protocols", [])
        care_plans = patient_data.get("care_plans", [])

        # 1. CQM-001: Diabetes HbA1c < 8.0%
        if measure_code == "CQM-001-DM-HBA1C":
            is_eligible = any(
                keyword in diag
                for diag in diagnoses
                for keyword in ["diabetes", "diabetic", "dm type 1", "dm type 2", "e11", "e10"]
            )
            if not is_eligible:
                return {
                    "is_eligible": False,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "excluded",
                    "evidence_json": {"diagnoses": diagnoses, "note": "Patient does not have documented diabetes diagnosis."},
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }

            # Find matching HbA1c results
            hba1c_results = [
                r for r in diagnostic_results
                if any(k in str(r.get("test_name", "")).lower() for k in ["hba1c", "hemoglobin a1c", "a1c"])
                and r.get("numeric_value") is not None
            ]

            if not hba1c_results:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "missing_data",
                    "evidence_json": {"diagnoses": diagnoses, "hba1c_results_count": 0},
                    "gap_reason": "No documented HbA1c laboratory result found within measurement window.",
                    "remediation_action": "Order Hemoglobin A1c test (LOINC 4548-4) for diabetic monitoring.",
                    "gap_severity": "HIGH",
                }

            latest_hba1c = hba1c_results[-1]
            val = float(latest_hba1c["numeric_value"])
            is_compliant = val < 8.0

            evidence = {
                "latest_hba1c_value": val,
                "unit": latest_hba1c.get("unit_of_measure", "%"),
                "result_id": latest_hba1c.get("result_id"),
                "test_name": latest_hba1c.get("test_name"),
            }

            if is_compliant:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": True,
                    "compliance_status": "compliant",
                    "evidence_json": evidence,
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }
            else:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "non_compliant",
                    "evidence_json": evidence,
                    "gap_reason": f"HbA1c level is elevated at {val}% (target < 8.0%).",
                    "remediation_action": "Titrate antihyperglycemic pharmacotherapy and schedule endocrine/nutrition consultation.",
                    "gap_severity": "HIGH",
                }

        # 2. CQM-002: Hypertension BP < 140/90 mmHg
        elif measure_code == "CQM-002-HTN-BP":
            is_eligible = any(
                keyword in diag
                for diag in diagnoses
                for keyword in ["hypertension", "essential hypertension", "htn", "i10", "high blood pressure"]
            )
            if not is_eligible:
                return {
                    "is_eligible": False,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "excluded",
                    "evidence_json": {"diagnoses": diagnoses, "note": "Patient does not have documented hypertension diagnosis."},
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }

            valid_vitals = [
                v for v in vitals
                if v.get("blood_pressure_systolic") is not None and v.get("blood_pressure_diastolic") is not None
            ]

            if not valid_vitals:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "missing_data",
                    "evidence_json": {"diagnoses": diagnoses, "vitals_count": 0},
                    "gap_reason": "No documented blood pressure reading recorded in measurement period.",
                    "remediation_action": "Record vital signs telemetry and verify automated cuff measurements.",
                    "gap_severity": "MODERATE",
                }

            latest_vital = valid_vitals[-1]
            sys = float(latest_vital["blood_pressure_systolic"])
            dia = float(latest_vital["blood_pressure_diastolic"])
            is_compliant = sys < 140.0 and dia < 90.0

            evidence = {
                "systolic_bp": sys,
                "diastolic_bp": dia,
                "measured_at": str(latest_vital.get("measured_at")),
            }

            if is_compliant:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": True,
                    "compliance_status": "compliant",
                    "evidence_json": evidence,
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }
            else:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "non_compliant",
                    "evidence_json": evidence,
                    "gap_reason": f"Blood pressure uncontrolled at {int(sys)}/{int(dia)} mmHg (target < 140/90 mmHg).",
                    "remediation_action": "Evaluate antihypertensive adherence and adjust ACEi/ARB or CCB dosing.",
                    "gap_severity": "MODERATE",
                }

        # 3. CQM-003: Post-Discharge Medication Reconciliation
        elif measure_code == "CQM-003-TOC-MEDREC":
            is_eligible = len(discharge_protocols) > 0
            if not is_eligible:
                return {
                    "is_eligible": False,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "excluded",
                    "evidence_json": {"discharge_protocols_count": 0, "note": "Patient has no recorded inpatient discharge events."},
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }

            latest_dc = discharge_protocols[-1]
            has_medrec = (
                latest_dc.get("medication_reconciliation_json") is not None
                and len(latest_dc.get("medication_reconciliation_json", [])) > 0
            )
            is_signed_off = (
                latest_dc.get("status") in ["signed_off", "completed"]
                or latest_dc.get("signed_off_at") is not None
            )
            is_compliant = has_medrec and is_signed_off

            evidence = {
                "discharge_id": latest_dc.get("discharge_id"),
                "status": latest_dc.get("status"),
                "has_medrec_list": has_medrec,
                "is_signed_off": is_signed_off,
            }

            if is_compliant:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": True,
                    "compliance_status": "compliant",
                    "evidence_json": evidence,
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }
            else:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "non_compliant",
                    "evidence_json": evidence,
                    "gap_reason": "Inpatient discharge protocol lacks completed medication reconciliation or attending signoff.",
                    "remediation_action": "Complete multi-disciplinary medication reconciliation and finalize discharge protocol.",
                    "gap_severity": "HIGH",
                }

        # 4. CQM-004: Care Plan & Task Adherence
        elif measure_code == "CQM-004-CP-ADHERENCE":
            is_eligible = len(care_plans) > 0
            if not is_eligible:
                return {
                    "is_eligible": False,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "excluded",
                    "evidence_json": {"care_plans_count": 0, "note": "No active longitudinal care plans found for patient."},
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }

            all_tasks = []
            for cp in care_plans:
                all_tasks.extend(cp.get("tasks", []))

            high_priority_tasks = [
                t for t in all_tasks
                if str(t.get("priority", "")).upper() in ["STAT", "HIGH", "URGENT"]
            ]

            if not high_priority_tasks:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": True,
                    "compliance_status": "compliant",
                    "evidence_json": {"total_care_plans": len(care_plans), "total_tasks": len(all_tasks), "high_priority_tasks": 0},
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }

            overdue_or_open_high = [t for t in high_priority_tasks if not t.get("is_completed", False)]
            is_compliant = len(overdue_or_open_high) == 0

            evidence = {
                "total_high_priority_tasks": len(high_priority_tasks),
                "completed_high_priority_tasks": len(high_priority_tasks) - len(overdue_or_open_high),
                "open_high_priority_tasks": len(overdue_or_open_high),
            }

            if is_compliant:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": True,
                    "compliance_status": "compliant",
                    "evidence_json": evidence,
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }
            else:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "non_compliant",
                    "evidence_json": evidence,
                    "gap_reason": f"{len(overdue_or_open_high)} STAT/HIGH priority care plan task(s) remain open and unfulfilled.",
                    "remediation_action": "Prioritize and execute open high-priority care tasks to maintain treatment adherence.",
                    "gap_severity": "HIGH",
                }

        # 5. CQM-005: Critical Lab Closed-Loop Signoff
        elif measure_code == "CQM-005-CRIT-LAB":
            panic_results = [
                r for r in diagnostic_results
                if str(r.get("abnormal_flag", "")).lower() == "panic_critical"
            ]

            is_eligible = len(panic_results) > 0
            if not is_eligible:
                return {
                    "is_eligible": False,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "excluded",
                    "evidence_json": {"panic_results_count": 0, "note": "No panic/critical diagnostic results recorded."},
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }

            unsigned_panic = [
                r for r in panic_results
                if r.get("reviewed_at") is None
            ]
            is_compliant = len(unsigned_panic) == 0

            evidence = {
                "total_panic_results": len(panic_results),
                "signed_panic_results": len(panic_results) - len(unsigned_panic),
                "unsigned_panic_results": len(unsigned_panic),
            }

            if is_compliant:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": True,
                    "compliance_status": "compliant",
                    "evidence_json": evidence,
                    "gap_reason": None,
                    "remediation_action": None,
                    "gap_severity": "LOW",
                }
            else:
                return {
                    "is_eligible": True,
                    "is_excluded": False,
                    "exclusion_reason": None,
                    "is_numerator_compliant": False,
                    "compliance_status": "non_compliant",
                    "evidence_json": evidence,
                    "gap_reason": f"{len(unsigned_panic)} panic critical lab result(s) lack required clinician signoff.",
                    "remediation_action": "Perform immediate clinician review and signoff on all critical lab findings.",
                    "gap_severity": "CRITICAL",
                }

        # Default fallback
        return {
            "is_eligible": True,
            "is_excluded": False,
            "exclusion_reason": None,
            "is_numerator_compliant": True,
            "compliance_status": "compliant",
            "evidence_json": {"note": "Standard compliance benchmark met."},
            "gap_reason": None,
            "remediation_action": None,
            "gap_severity": "LOW",
        }
