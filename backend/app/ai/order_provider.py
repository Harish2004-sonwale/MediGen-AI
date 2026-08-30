"""Deterministic AI Provider for Computerized Physician Order Entry (CPOE) and Panic Result Evaluation.

Phase 9.0.13: Computerized Physician Order Entry (CPOE), Diagnostic Order Lifecycle & Closed-Loop Critical Result Tracking.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseOrderVerificationProvider(ABC):
    """Abstract interface for clinical order verification and bundle generation."""

    @abstractmethod
    def suggest_order_bundle(
        self,
        protocol_name: Optional[str] = None,
        indication: Optional[str] = None,
        diagnoses: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Synthesize standardized diagnostic and therapeutic order bundles."""
        pass

    @abstractmethod
    def verify_order_safety(
        self,
        order_type: str,
        order_category: str,
        recent_order_types: list[str],
        active_conditions: list[str],
    ) -> list[dict[str, str]]:
        """Verify order for duplicates, timing redundancies, and contraindications."""
        pass

    @abstractmethod
    def evaluate_panic_threshold(
        self,
        test_name: str,
        numeric_value: Optional[float],
        ref_low: Optional[float] = None,
        ref_high: Optional[float] = None,
        crit_low: Optional[float] = None,
        crit_high: Optional[float] = None,
    ) -> str:
        """Classify result into normal, abnormal_low, abnormal_high, or panic_critical."""
        pass


class MockOrderVerificationProvider(BaseOrderVerificationProvider):
    """Deterministic, 100% offline heuristic engine for CPOE and critical lab evaluation."""

    # Default critical panic thresholds
    PANIC_THRESHOLDS: dict[str, dict[str, float]] = {
        "potassium": {"crit_low": 2.8, "crit_high": 6.2, "ref_low": 3.5, "ref_high": 5.0},
        "sodium": {"crit_low": 120.0, "crit_high": 160.0, "ref_low": 135.0, "ref_high": 145.0},
        "glucose": {"crit_low": 45.0, "crit_high": 450.0, "ref_low": 70.0, "ref_high": 100.0},
        "troponin": {"crit_high": 0.04, "ref_high": 0.01},
        "lactate": {"crit_high": 4.0, "ref_high": 2.0},
        "hemoglobin": {"crit_low": 7.0, "crit_high": 20.0, "ref_low": 12.0, "ref_high": 16.0},
        "platelets": {"crit_low": 30.0, "crit_high": 1000.0, "ref_low": 150.0, "ref_high": 450.0},
        "wbc": {"crit_low": 2.0, "crit_high": 30.0, "ref_low": 4.5, "ref_high": 11.0},
    }

    def suggest_order_bundle(
        self,
        protocol_name: Optional[str] = None,
        indication: Optional[str] = None,
        diagnoses: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        p_name = (protocol_name or "").lower().strip()
        ind_str = (indication or "").lower()
        diag_str = " ".join(diagnoses or []).lower()

        warnings = []

        if "chest_pain" in p_name or "acs" in p_name or "chest pain" in ind_str or "myocardial" in diag_str:
            proto_key = "Chest Pain / Acute Coronary Syndrome Bundle"
            rationale = "Targeted cardiovascular workup for suspected myocardial ischemia or acute coronary syndrome."
            items = [
                {
                    "order_category": "laboratory",
                    "order_type": "troponin_i_high_sensitivity",
                    "priority": "stat",
                    "clinical_indication": "Rule out acute myocardial infarction",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "basic_metabolic_panel",
                    "priority": "routine",
                    "clinical_indication": "Assess baseline renal function and electrolyte stability",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "complete_blood_count",
                    "priority": "routine",
                    "clinical_indication": "Evaluate anemia and inflammatory markers",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "imaging",
                    "order_type": "chest_xray_2_views",
                    "priority": "urgent",
                    "clinical_indication": "Evaluate pulmonary vascular congestion and mediastinal silhouette",
                },
            ]
        elif "sepsis" in p_name or "fever" in ind_str or "septic" in diag_str:
            proto_key = "Sepsis Early Intervention Bundle"
            rationale = "Urgent diagnostic pan-culture, tissue perfusion assessment, and organ dysfunction evaluation."
            items = [
                {
                    "order_category": "laboratory",
                    "order_type": "serum_lactate",
                    "priority": "stat",
                    "clinical_indication": "Evaluate cellular hypoxia and tissue hypoperfusion",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "blood_cultures_x2",
                    "priority": "stat",
                    "clinical_indication": "Bacteremia identification prior to broad-spectrum antimicrobials",
                    "specimen_source": "Peripheral venous (2 sites)",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "complete_blood_count_with_diff",
                    "priority": "stat",
                    "clinical_indication": "Assess leukocytosis, bandemia, and thrombocytopenia",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "comprehensive_metabolic_panel",
                    "priority": "stat",
                    "clinical_indication": "Renal and hepatic organ dysfunction assessment",
                    "specimen_source": "Venous blood",
                },
            ]
        elif "dka" in p_name or "ketoacidosis" in ind_str or "diabetes" in diag_str:
            proto_key = "Diabetic Ketoacidosis & Hyperglycemia Protocol"
            rationale = "Rapid metabolic evaluation of acid-base balance, anion gap, and glycemic decompensation."
            items = [
                {
                    "order_category": "laboratory",
                    "order_type": "basic_metabolic_panel",
                    "priority": "stat",
                    "clinical_indication": "Serial potassium monitoring and anion gap calculation",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "venous_blood_gas",
                    "priority": "stat",
                    "clinical_indication": "Measure venous pH and bicarbonate deficit",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "beta_hydroxybutyrate_quantitative",
                    "priority": "stat",
                    "clinical_indication": "Confirm presence and clearance of circulating serum ketones",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "hemoglobin_a1c",
                    "priority": "routine",
                    "clinical_indication": "Assess 90-day baseline glycemic control",
                    "specimen_source": "Venous blood",
                },
            ]
        else:
            proto_key = "General Clinical Inpatient Admission Set"
            rationale = "Comprehensive baseline metabolic, hematologic, and diagnostic screening."
            items = [
                {
                    "order_category": "laboratory",
                    "order_type": "complete_blood_count",
                    "priority": "routine",
                    "clinical_indication": "Baseline hematology screen",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "comprehensive_metabolic_panel",
                    "priority": "routine",
                    "clinical_indication": "Electrolyte and organ function baseline",
                    "specimen_source": "Venous blood",
                },
                {
                    "order_category": "laboratory",
                    "order_type": "urinalysis_complete",
                    "priority": "routine",
                    "clinical_indication": "Renal screening and occult urinary tract infection",
                    "specimen_source": "Clean catch urine",
                },
            ]

        return {
            "protocol_name": proto_key,
            "clinical_rationale": rationale,
            "suggested_orders": items,
            "pre_order_safety_warnings": warnings,
        }

    def verify_order_safety(
        self,
        order_type: str,
        order_category: str,
        recent_order_types: list[str],
        active_conditions: list[str],
    ) -> list[dict[str, str]]:
        flags = []
        ot_clean = order_type.lower().strip()

        # 1. Duplicate order check
        if ot_clean in [r.lower().strip() for r in recent_order_types]:
            flags.append({
                "severity": "WARNING",
                "code": "DUPLICATE_ORDER_ALERT",
                "message": f"Identical order '{order_type}' was placed within the preceding 24 hours. Verify clinical necessity.",
            })

        # 2. Contrast & Renal impairment safety
        if "contrast" in ot_clean:
            renal_terms = ["renal", "kidney", "nephropathy", "aki", "ckd", "creatinine"]
            if any(term in c.lower() for term in renal_terms for c in active_conditions):
                flags.append({
                    "severity": "CRITICAL",
                    "code": "CONTRAST_NEPHROPATHY_RISK",
                    "message": "Patient has active renal condition. Review eGFR and hydration protocol prior to administering iodinated or gadolinium contrast.",
                })

        return flags

    def evaluate_panic_threshold(
        self,
        test_name: str,
        numeric_value: Optional[float],
        ref_low: Optional[float] = None,
        ref_high: Optional[float] = None,
        crit_low: Optional[float] = None,
        crit_high: Optional[float] = None,
    ) -> str:
        if numeric_value is None:
            return "normal"

        t_lower = test_name.lower()

        # Look up built-in defaults if not explicitly provided
        for key, limits in self.PANIC_THRESHOLDS.items():
            if key in t_lower:
                crit_low = crit_low if crit_low is not None else limits.get("crit_low")
                crit_high = crit_high if crit_high is not None else limits.get("crit_high")
                ref_low = ref_low if ref_low is not None else limits.get("ref_low")
                ref_high = ref_high if ref_high is not None else limits.get("ref_high")
                break

        # Check critical panic thresholds first
        if crit_low is not None and numeric_value <= crit_low:
            return "panic_critical"
        if crit_high is not None and numeric_value >= crit_high:
            return "panic_critical"

        # Check abnormal thresholds
        if ref_low is not None and numeric_value < ref_low:
            return "abnormal_low"
        if ref_high is not None and numeric_value > ref_high:
            return "abnormal_high"

        return "normal"


_order_provider_instance: Optional[BaseOrderVerificationProvider] = None


def get_order_provider() -> BaseOrderVerificationProvider:
    """Return singleton instance of the deterministic order verification provider."""
    global _order_provider_instance
    if _order_provider_instance is None:
        _order_provider_instance = MockOrderVerificationProvider()
    return _order_provider_instance
