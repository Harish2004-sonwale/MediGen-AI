"""Multi-Agent Clinical Orchestrator & Deterministic Reasoning Providers.

Phase 9.0.17: Advanced Clinical AI Agents & Autonomous Care Coordination.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Optional


def _compute_sha256(payload: Any) -> str:
    """Compute deterministic SHA-256 hash over JSON-serializable payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _sanitize_untrusted_text(text: Optional[str]) -> str:
    """Sanitize clinical text to neutralize prompt injection or script execution attempts."""
    if not text:
        return ""
    # Strip potential instruction injection attempts or script tags
    sanitized = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r"(ignore\s+all\s+previous\s+instructions|system\s+prompt|sudo|chmod)", "[SANITIZED]", sanitized, flags=re.IGNORECASE)
    return sanitized.strip()


class BaseClinicalAgentProvider(ABC):
    """Abstract interface for clinical AI agent execution and care coordination."""

    @abstractmethod
    def orchestrate_master_run(
        self, patient_id: str, context: dict[str, Any], requested_subagents: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Execute coordinated multi-agent care synthesis across specialized agents."""
        pass


class MockClinicalAgentProvider(BaseClinicalAgentProvider):
    """Deterministic offline clinical agent orchestration provider."""

    def __init__(self, provider_version: str = "2026.1-deterministic"):
        self.provider_version = provider_version

    def orchestrate_master_run(
        self, patient_id: str, context: dict[str, Any], requested_subagents: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Execute multi-agent reasoning and synthesize prioritized recommendations."""
        subagents = requested_subagents or [
            "clinical_context",
            "risk_surveillance",
            "care_coordination",
            "diagnostic_followup",
            "medication_safety",
            "quality_gap",
            "rpm_telehealth",
            "transition_discharge",
            "trial_genomics",
        ]

        recommendations: list[dict[str, Any]] = []

        # 1. Clinical Context Aggregator
        if "clinical_context" in subagents:
            ctx_rec = self._evaluate_context_summary(patient_id, context)
            if ctx_rec:
                recommendations.append(ctx_rec)

        # 2. Risk Surveillance Agent
        if "risk_surveillance" in subagents:
            risk_recs = self._evaluate_risk_surveillance(patient_id, context)
            recommendations.extend(risk_recs)

        # 3. Care Coordination Agent
        if "care_coordination" in subagents:
            coord_recs = self._evaluate_care_coordination(patient_id, context)
            recommendations.extend(coord_recs)

        # 4. Diagnostic Follow-Up Agent
        if "diagnostic_followup" in subagents:
            diag_recs = self._evaluate_diagnostic_followup(patient_id, context)
            recommendations.extend(diag_recs)

        # 5. Medication Safety Agent
        if "medication_safety" in subagents:
            med_recs = self._evaluate_medication_safety(patient_id, context)
            recommendations.extend(med_recs)

        # 6. Quality Gap Agent
        if "quality_gap" in subagents:
            q_recs = self._evaluate_quality_gaps(patient_id, context)
            recommendations.extend(q_recs)

        # 7. RPM / Telehealth Agent
        if "rpm_telehealth" in subagents:
            rpm_recs = self._evaluate_rpm_telehealth(patient_id, context)
            recommendations.extend(rpm_recs)

        # 8. Transition & Discharge Agent
        if "transition_discharge" in subagents:
            trans_recs = self._evaluate_transition_discharge(patient_id, context)
            recommendations.extend(trans_recs)

        # 9. Trial & Precision Oncology Agent
        if "trial_genomics" in subagents:
            trial_recs = self._evaluate_trial_genomics(patient_id, context)
            recommendations.extend(trial_recs)

        # Sort recommendations by priority (urgent > high > medium > low)
        priority_weight = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_weight.get(r.get("priority", "medium"), 2))

        # Overall synthesis summary
        urgent_count = sum(1 for r in recommendations if r.get("priority") == "urgent")
        high_count = sum(1 for r in recommendations if r.get("priority") == "high")
        approval_required_count = sum(
            1 for r in recommendations if r.get("action_class") in ("CLINICIAN_APPROVAL_REQUIRED", "HIGH_RISK")
        )

        overall_summary = (
            f"Multi-Agent Care Coordination synthesis completed for patient {patient_id}. "
            f"Evaluated {len(subagents)} specialized agents; generated {len(recommendations)} actionable recommendations "
            f"({urgent_count} urgent, {high_count} high priority, {approval_required_count} requiring formal clinician sign-off)."
        )

        provenance_payload = {
            "patient_id": patient_id,
            "subagents": subagents,
            "recommendations_count": len(recommendations),
            "recommendation_hashes": [r.get("provenance_hash") for r in recommendations],
            "provider_version": self.provider_version,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
        provenance_hash = _compute_sha256(provenance_payload)

        return {
            "patient_id": patient_id,
            "overall_summary": overall_summary,
            "recommendations": recommendations,
            "provenance_hash": provenance_hash,
            "provider_version": self.provider_version,
        }

    # =========================================================================
    # SPECIALIZED AGENT EVALUATORS
    # =========================================================================

    def _evaluate_context_summary(self, patient_id: str, context: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Clinical Context Agent: Synthesizes longitudinal facts."""
        encounters = context.get("encounters", [])
        vitals = context.get("vitals", [])
        diagnoses = context.get("diagnoses", [])
        care_plans = context.get("care_plans", [])

        summary_text = (
            f"Longitudinal Clinical Context: {len(encounters)} clinical encounters, "
            f"{len(diagnoses)} documented diagnoses ({', '.join(diagnoses[:3]) if diagnoses else 'None'}), "
            f"{len(vitals)} vital telemetry streams, {len(care_plans)} active care plans."
        )

        rec_payload = {
            "category": "clinical_context_summary",
            "title": "Longitudinal Clinical Profile Synthesized",
            "description": summary_text,
            "rationale": "Comprehensive multi-domain clinical baseline aggregation for clinical decision support.",
            "priority": "low",
            "action_class": "READ_ONLY",
            "suggested_action_type": "view_summary",
            "suggested_action_payload_json": {"diagnoses_count": len(diagnoses), "encounters_count": len(encounters)},
            "evidence_references": [
                {
                    "entity_type": "encounter",
                    "entity_identifier": enc.get("encounter_id", f"ENC-{idx}"),
                    "title": f"Encounter: {enc.get('chief_complaint', 'Clinical visit')}",
                    "excerpt": _sanitize_untrusted_text(enc.get("assessment", enc.get("clinical_notes", ""))),
                    "confidence_score": 1.0,
                }
                for idx, enc in enumerate(encounters[:3])
            ],
        }
        rec_payload["provenance_hash"] = _compute_sha256(rec_payload)
        return rec_payload

    def _evaluate_risk_surveillance(self, patient_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Risk Surveillance Agent: Identifies acute alerts and severe vital drift."""
        recommendations = []
        alerts = context.get("alerts", [])
        vitals = context.get("vitals", [])
        rpm_alerts = context.get("rpm_alerts", [])

        # 1. Unacknowledged Critical Alerts
        crit_alerts = [a for a in alerts if a.get("severity") in ("CRITICAL", "critical", "HIGH", "high") and a.get("status") in ("ACTIVE", "active", "open")]
        for a in crit_alerts:
            rec = {
                "category": "risk_escalation",
                "title": f"Critical CDS Alert Requires Clinician Acknowledgment: {a.get('title', 'Acute Alert')}",
                "description": f"Unacknowledged critical alert: {_sanitize_untrusted_text(a.get('message', ''))}",
                "rationale": "Critical clinical alerts require urgent physician evaluation to prevent adverse outcomes.",
                "priority": "urgent",
                "action_class": "HIGH_RISK",
                "suggested_action_type": "acknowledge_alert",
                "suggested_action_payload_json": {"alert_id": a.get("alert_id")},
                "evidence_references": [
                    {
                        "entity_type": "alert",
                        "entity_identifier": str(a.get("alert_id", "ALR-001")),
                        "title": a.get("title", "Critical Alert"),
                        "excerpt": _sanitize_untrusted_text(a.get("message", "")),
                        "confidence_score": 1.0,
                    }
                ],
            }
            rec["provenance_hash"] = _compute_sha256(rec)
            recommendations.append(rec)

        # 2. RPM Escalation Alerts
        for ra in rpm_alerts:
            if ra.get("status") in ("triggered", "open", "active"):

                rec = {
                    "category": "risk_escalation",
                    "title": f"RPM Telemetry Deterioration: {ra.get('reason', 'Vital Drift')}",
                    "description": f"Continuous RPM monitoring triggered escalation ({ra.get('severity', 'high')}): {_sanitize_untrusted_text(ra.get('recommended_action', ''))}",
                    "rationale": "Sustained physiological drift warrants proactive clinical triage.",
                    "priority": "high" if ra.get("severity") != "critical" else "urgent",
                    "action_class": "CLINICIAN_APPROVAL_REQUIRED",
                    "suggested_action_type": "triage_rpm_escalation",
                    "suggested_action_payload_json": {"escalation_id": ra.get("alert_id")},
                    "evidence_references": [
                        {
                            "entity_type": "rpm_observation",
                            "entity_identifier": str(ra.get("alert_id", "RPM-ALR-001")),
                            "title": ra.get("reason", "RPM Alert"),
                            "excerpt": _sanitize_untrusted_text(ra.get("reason", "")),
                            "confidence_score": 0.95,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        return recommendations

    def _evaluate_care_coordination(self, patient_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Care Coordination Agent: Dispatches overdue care tasks and follow-up reviews."""
        recommendations = []
        care_tasks = context.get("care_tasks", [])

        # Overdue or high-priority pending care tasks
        pending_tasks = [t for t in care_tasks if t.get("status") in ("pending", "in_progress", "PENDING", "IN_PROGRESS")]
        for t in pending_tasks:
            if t.get("priority") in ("high", "urgent", "HIGH", "URGENT"):
                rec = {
                    "category": "care_task_dispatch",
                    "title": f"Prioritized Care Coordination Task: {t.get('title', 'Care Task')}",
                    "description": f"Outstanding high-priority care task assigned to {t.get('assigned_role', 'care_team')}: {_sanitize_untrusted_text(t.get('description', ''))}",
                    "rationale": "Closing active care coordination tasks ensures multi-disciplinary care continuity.",
                    "priority": "high",
                    "action_class": "CLINICIAN_APPROVAL_REQUIRED",
                    "suggested_action_type": "complete_care_task",
                    "suggested_action_payload_json": {"task_id": t.get("task_id")},
                    "evidence_references": [
                        {
                            "entity_type": "care_task",
                            "entity_identifier": str(t.get("task_id", "TASK-001")),
                            "title": t.get("title", "Care Task"),
                            "excerpt": _sanitize_untrusted_text(t.get("description", "")),
                            "confidence_score": 0.95,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        return recommendations

    def _evaluate_diagnostic_followup(self, patient_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Diagnostic Follow-Up Agent: Detects open-loop diagnostic orders and critical results."""
        recommendations = []
        orders = context.get("orders", [])
        results = context.get("results", [])

        # 1. Unacknowledged Critical Diagnostic Results
        for r in results:
            if r.get("is_critical") and r.get("status") != "reviewed":
                rec = {
                    "category": "diagnostic_loop_closure",
                    "title": f"Critical Diagnostic Result Awaiting Clinician Review: {r.get('test_name', 'Lab Result')}",
                    "description": f"Critical value detected ({r.get('value')} {r.get('unit', '')}): {_sanitize_untrusted_text(r.get('interpretation', ''))}. Clinician sign-off required.",
                    "rationale": "Closed-loop diagnostic result management prevents delayed treatment for critical abnormalities.",
                    "priority": "urgent",
                    "action_class": "HIGH_RISK",
                    "suggested_action_type": "review_diagnostic_result",
                    "suggested_action_payload_json": {"result_id": r.get("result_id")},
                    "evidence_references": [
                        {
                            "entity_type": "result",
                            "entity_identifier": str(r.get("result_id", "RES-001")),
                            "title": f"Critical Result: {r.get('test_name')}",
                            "excerpt": f"Value: {r.get('value')} {r.get('unit', '')} | Status: {r.get('status')}",
                            "confidence_score": 1.0,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        # 2. Open Orders without Results
        for o in orders:
            if o.get("status") == "in_progress" and o.get("priority") in ("stat", "urgent"):
                rec = {
                    "category": "diagnostic_loop_closure",
                    "title": f"Pending STAT Diagnostic Order: {o.get('order_name', 'Order')}",
                    "description": f"STAT priority order {o.get('order_id')} is currently awaiting lab processing.",
                    "rationale": "STAT orders require close tracking for timely result availability.",
                    "priority": "high",
                    "action_class": "RECOMMENDATION",
                    "suggested_action_type": "track_order_status",
                    "suggested_action_payload_json": {"order_id": o.get("order_id")},
                    "evidence_references": [
                        {
                            "entity_type": "order",
                            "entity_identifier": str(o.get("order_id", "ORD-001")),
                            "title": f"Order: {o.get('order_name')}",
                            "excerpt": f"Status: {o.get('status')} | Category: {o.get('order_category')}",
                            "confidence_score": 0.9,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        return recommendations

    def _evaluate_medication_safety(self, patient_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Medication Safety Agent: Flags duplications and medication reconciliation opportunities."""
        recommendations = []
        medications = context.get("medications", [])
        allergies = context.get("allergies", [])

        # Check for duplicated therapeutic classes or duplicate active medications
        seen_names: dict[str, list[dict[str, Any]]] = {}
        for m in medications:
            raw_name = m.get("name", "").strip().lower()
            if raw_name:
                clean_name = raw_name.split()[0]
                seen_names.setdefault(clean_name, []).append(m)


        for name, dup_list in seen_names.items():
            if len(dup_list) > 1:
                rec = {
                    "category": "medication_safety_warning",
                    "title": f"Potential Duplicate Medication Prescribed: {name.title()}",
                    "description": f"Detected {len(dup_list)} active prescriptions for {name.title()}. Clinician reconciliation recommended.",
                    "rationale": "Duplicate active prescriptions carry risk of accidental drug toxicity.",
                    "priority": "high",
                    "action_class": "CLINICIAN_APPROVAL_REQUIRED",
                    "suggested_action_type": "flag_medication_reconciliation",
                    "suggested_action_payload_json": {"medication_name": name},
                    "evidence_references": [
                        {
                            "entity_type": "encounter",
                            "entity_identifier": str(dup_list[0].get("encounter_id", "MED-001")),
                            "title": f"Medication Record: {name.title()}",
                            "excerpt": f"Multiple active entries found for {name.title()}",
                            "confidence_score": 0.95,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        return recommendations

    def _evaluate_quality_gaps(self, patient_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Quality Gap Agent: Recommends outreach for open HEDIS/MIPS compliance gaps."""
        recommendations = []
        quality_gaps = context.get("quality_gaps", [])

        open_gaps = [g for g in quality_gaps if g.get("status") in ("open", "OPEN")]
        for g in open_gaps:
            rec = {
                "category": "quality_outreach",
                "title": f"Clinical Quality Gap Outreach: {g.get('measure_name', 'CQM Measure')}",
                "description": f"Patient has an open care compliance gap ({g.get('measure_id')}). Recommended clinical outreach: {_sanitize_untrusted_text(g.get('recommended_action', 'Schedule screening.'))}",
                "rationale": "Proactive quality measure gap closure enhances preventive health outcomes and HEDIS compliance.",
                "priority": "medium",
                "action_class": "CLINICIAN_APPROVAL_REQUIRED",
                "suggested_action_type": "schedule_screening_outreach",
                "suggested_action_payload_json": {"gap_id": g.get("gap_id"), "measure_id": g.get("measure_id")},
                "evidence_references": [
                    {
                        "entity_type": "quality_gap",
                        "entity_identifier": str(g.get("gap_id", "GAP-001")),
                        "title": f"Quality Gap: {g.get('measure_id')}",
                        "excerpt": _sanitize_untrusted_text(g.get("recommended_action", "")),
                        "confidence_score": 0.95,
                    }
                ],
            }
            rec["provenance_hash"] = _compute_sha256(rec)
            recommendations.append(rec)

        return recommendations

    def _evaluate_rpm_telehealth(self, patient_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """RPM / Telehealth Agent: Flags survey safety flags and recommends virtual check-ins."""
        recommendations = []
        prom_responses = context.get("prom_responses", [])

        for pr in prom_responses:
            if pr.get("safety_flag"):
                rec = {
                    "category": "telehealth_referral",
                    "title": f"Urgent Behavioral Safety Flag on {pr.get('survey_code', 'PROM')} Survey",
                    "description": f"Positive safety flag detected on {pr.get('survey_code')} (Score: {pr.get('score')}, Severity: {pr.get('severity')}). Recommended immediate clinical telehealth consultation.",
                    "rationale": "High-risk PROM survey answers (e.g. PHQ-9 Q9) mandate expedited clinical contact.",
                    "priority": "urgent",
                    "action_class": "HIGH_RISK",
                    "suggested_action_type": "schedule_telehealth_consult",
                    "suggested_action_payload_json": {"survey_code": pr.get("survey_code"), "response_id": pr.get("response_id")},
                    "evidence_references": [
                        {
                            "entity_type": "observation",
                            "entity_identifier": str(pr.get("response_id", "PROM-001")),
                            "title": f"Survey Response: {pr.get('survey_code')}",
                            "excerpt": f"Severity: {pr.get('severity')} | Safety Flag: {pr.get('safety_flag')}",
                            "confidence_score": 1.0,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        return recommendations

    def _evaluate_transition_discharge(self, patient_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Transition Agent: Monitors pending handoff items and post-discharge tasks."""
        recommendations = []
        handoffs = context.get("handoffs", [])
        discharges = context.get("discharges", [])

        for h in handoffs:
            if h.get("status") == "active" and h.get("illness_severity") in ("unstable", "critical"):
                rec = {
                    "category": "transition_followup",
                    "title": f"Active Clinical Handoff Requires Care Continuity: {h.get('handoff_id')}",
                    "description": f"Active {h.get('handoff_type', 'I-PASS')} handoff for patient with {h.get('illness_severity')} severity: {_sanitize_untrusted_text(h.get('action_items_text', ''))}",
                    "rationale": "Care transition handoffs ensure seamless shift-to-shift and multi-disciplinary communication.",
                    "priority": "high",
                    "action_class": "CLINICIAN_APPROVAL_REQUIRED",
                    "suggested_action_type": "review_handoff",
                    "suggested_action_payload_json": {"handoff_id": h.get("handoff_id")},
                    "evidence_references": [
                        {
                            "entity_type": "encounter",
                            "entity_identifier": str(h.get("handoff_id", "HO-001")),
                            "title": f"Handoff: {h.get('handoff_type')}",
                            "excerpt": _sanitize_untrusted_text(h.get("action_items_text", "")),
                            "confidence_score": 0.95,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        return recommendations

    def _evaluate_trial_genomics(self, patient_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Trial & Precision Oncology Agent: Evaluates trial eligibility for oncologist review."""
        recommendations = []
        trial_matches = context.get("trial_matches", [])
        precision_eligibilities = context.get("precision_eligibilities", [])

        # 1. Matched Clinical Trials
        for tm in trial_matches:
            if tm.get("match_status") in ("MATCHED", "POTENTIAL_MATCH") and tm.get("clinician_review_status") == "pending_review":
                rec = {
                    "category": "trial_screening",
                    "title": f"Eligible Clinical Trial Candidate: {tm.get('trial_title', 'Clinical Trial')}",
                    "description": f"Patient matched ({tm.get('match_score', 100):.0f}% score) for protocol {tm.get('trial_identifier')}: {_sanitize_untrusted_text(tm.get('overall_explanation', ''))}",
                    "rationale": "High-confidence clinical trial matching expands innovative therapeutic options for oncology patients.",
                    "priority": "high",
                    "action_class": "CLINICIAN_APPROVAL_REQUIRED",
                    "suggested_action_type": "review_trial_match",
                    "suggested_action_payload_json": {"match_id": tm.get("match_id"), "trial_id": tm.get("trial_identifier")},
                    "evidence_references": [
                        {
                            "entity_type": "trial_match",
                            "entity_identifier": str(tm.get("match_id", "TM-001")),
                            "title": f"Trial: {tm.get('trial_identifier')}",
                            "excerpt": _sanitize_untrusted_text(tm.get("overall_explanation", "")),
                            "confidence_score": 1.0,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        # 2. Precision Targeted Oncology Therapies
        for pe in precision_eligibilities:
            if pe.get("eligibility_status") == "ELIGIBLE" and pe.get("clinician_review_status") == "pending_review":
                rec = {
                    "category": "trial_screening",
                    "title": f"Actionable Targeted Precision Oncology Candidate: {pe.get('recommended_intervention')}",
                    "description": f"Detected actionable biomarker {pe.get('gene_symbol')} {pe.get('variant_name')} eligible for {pe.get('recommended_intervention')} ({pe.get('drug_class')}). Evidence: {pe.get('evidence_source')}.",
                    "rationale": "NCCN/FDA guideline-concordant precision therapy decision support.",
                    "priority": "high",
                    "action_class": "HIGH_RISK",
                    "suggested_action_type": "review_precision_eligibility",
                    "suggested_action_payload_json": {"eligibility_id": pe.get("eligibility_id")},
                    "evidence_references": [
                        {
                            "entity_type": "biomarker",
                            "entity_identifier": f"{pe.get('gene_symbol')}_{pe.get('variant_name')}",
                            "title": f"Biomarker: {pe.get('gene_symbol')} {pe.get('variant_name')}",
                            "excerpt": f"Evidence: {pe.get('evidence_source')}",
                            "confidence_score": 1.0,
                        }
                    ],
                }
                rec["provenance_hash"] = _compute_sha256(rec)
                recommendations.append(rec)

        return recommendations
