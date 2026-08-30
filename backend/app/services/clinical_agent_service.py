"""Service layer for Clinical AI Agents & Autonomous Care Coordination.

Phase 9.0.17: Advanced Clinical AI Agents & Autonomous Care Coordination.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.ai.agent_orchestrator_provider import MockClinicalAgentProvider, _compute_sha256
from app.models.agents import (
    AgentEvidenceReference,
    ClinicalAgentDefinition,
    ClinicalAgentRecommendation,
    ClinicalAgentRun,
)
from app.models.alert import ClinicalAlert
from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.discharge import DischargeProtocol
from app.models.encounter import Encounter
from app.models.handoff import ClinicalHandoff
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.patient import Patient
from app.models.quality import QualityMeasureGap
from app.models.rpm import PROMResponse, RPMEscalationAlert, RPMObservation
from app.models.trials import PrecisionTreatmentEligibility, TrialMatch
from app.models.vital import VitalTelemetry
from app.schemas.agents import (
    AgentRunStatus,
    AgentType,
    ApprovalStatus,
    CareCoordinationSynthesisResponse,
    ClinicalAgentRecommendationResponse,
    RecommendationActionClass,
)

logger = logging.getLogger("medigen.agents")


class ClinicalAgentService:
    """Orchestrates multi-agent execution, structured context generation, and clinician review governance."""

    def __init__(self, provider: Optional[MockClinicalAgentProvider] = None):
        self.provider = provider or MockClinicalAgentProvider()

    def _resolve_patient(self, db: Session, patient_id_or_str: Any) -> Patient:
        """Resolve Patient ORM instance from integer PK or business identifier."""
        if isinstance(patient_id_or_str, int) or (
            isinstance(patient_id_or_str, str) and patient_id_or_str.isdigit()
        ):
            stmt = select(Patient).where(Patient.id == int(patient_id_or_str))
        else:
            stmt = select(Patient).where(Patient.patient_id == str(patient_id_or_str))
        patient = db.execute(stmt).scalar_one_or_none()
        if not patient:
            raise ValueError(f"Patient '{patient_id_or_str}' was not found.")
        return patient

    # =========================================================================
    # 1. SEED DEFAULT AGENT DEFINITIONS
    # =========================================================================

    def seed_default_agents(self, db: Session) -> list[ClinicalAgentDefinition]:
        """Seed standard clinical AI agent definitions if not already present."""
        default_agents = [
            {
                "agent_id": "AGENT-CONTEXT-001",
                "name": "Clinical Context Aggregator",
                "agent_type": "clinical_context",
                "description": "Synthesizes multi-domain longitudinal encounters, diagnoses, medications, and vitals baseline.",
                "default_action_class": "READ_ONLY",
            },
            {
                "agent_id": "AGENT-RISK-002",
                "name": "Clinical Risk Surveillance Agent",
                "agent_type": "risk_surveillance",
                "description": "Continuously evaluates acute CDS alerts, severe vital trends, and telemetry deterioration.",
                "default_action_class": "HIGH_RISK",
            },
            {
                "agent_id": "AGENT-COORD-003",
                "name": "Care Coordination Agent",
                "agent_type": "care_coordination",
                "description": "Identifies outstanding care tasks and dispatches follow-ups across care teams.",
                "default_action_class": "CLINICIAN_APPROVAL_REQUIRED",
            },
            {
                "agent_id": "AGENT-DIAG-004",
                "name": "Diagnostic Follow-Up Agent",
                "agent_type": "diagnostic_followup",
                "description": "Closes diagnostic loops by tracking critical results and open orders.",
                "default_action_class": "HIGH_RISK",
            },
            {
                "agent_id": "AGENT-MED-005",
                "name": "Medication Safety Agent",
                "agent_type": "medication_safety",
                "description": "Detects duplicate active prescriptions and flags medication reconciliation needs.",
                "default_action_class": "CLINICIAN_APPROVAL_REQUIRED",
            },
            {
                "agent_id": "AGENT-QUAL-006",
                "name": "Clinical Quality Gap Agent",
                "agent_type": "quality_gap",
                "description": "Connects open HEDIS/MIPS compliance gaps to preventive screening workflows.",
                "default_action_class": "CLINICIAN_APPROVAL_REQUIRED",
            },
            {
                "agent_id": "AGENT-RPM-007",
                "name": "RPM & Telehealth Agent",
                "agent_type": "rpm_telehealth",
                "description": "Monitors PROM behavioral safety flags and physiological drift for virtual check-ins.",
                "default_action_class": "HIGH_RISK",
            },
            {
                "agent_id": "AGENT-TRANS-008",
                "name": "Transition & Discharge Agent",
                "agent_type": "transition_discharge",
                "description": "Monitors clinical handoffs and post-discharge care continuity requirements.",
                "default_action_class": "CLINICIAN_APPROVAL_REQUIRED",
            },
            {
                "agent_id": "AGENT-TRIALS-009",
                "name": "Trial & Precision Oncology Agent",
                "agent_type": "trial_genomics",
                "description": "Evaluates clinical trial matches and actionable targeted precision oncology therapies.",
                "default_action_class": "HIGH_RISK",
            },
            {
                "agent_id": "AGENT-MASTER-010",
                "name": "Master Care Orchestrator",
                "agent_type": "master_orchestrator",
                "description": "Coordinates specialized clinical agents and produces a prioritized, auditable care coordination plan.",
                "default_action_class": "CLINICIAN_APPROVAL_REQUIRED",
            },
        ]

        seeded = []
        for def_data in default_agents:
            existing = db.execute(
                select(ClinicalAgentDefinition).where(ClinicalAgentDefinition.agent_id == def_data["agent_id"])
            ).scalar_one_or_none()
            if not existing:
                agent = ClinicalAgentDefinition(
                    agent_id=def_data["agent_id"],
                    name=def_data["name"],
                    agent_type=def_data["agent_type"],
                    description=def_data["description"],
                    version="1.0.0",
                    is_active=True,
                    default_action_class=def_data["default_action_class"],
                )
                db.add(agent)
                seeded.append(agent)
            else:
                seeded.append(existing)
        db.commit()
        return seeded

    # =========================================================================
    # 2. STRUCTURED PATIENT CONTEXT BUILDER
    # =========================================================================

    def build_patient_context(self, db: Session, patient_id_or_str: Any) -> dict[str, Any]:
        """Aggregate patient clinical entities into a structured, sanitized snapshot."""
        patient = self._resolve_patient(db, patient_id_or_str)

        # 1. Encounters
        enc_stmt = select(Encounter).where(Encounter.patient_id == patient.id).order_by(desc(Encounter.created_at))
        encounters = list(db.execute(enc_stmt).scalars().all())

        # Extract diagnoses
        diagnoses = []
        medications = []
        for enc in encounters:
            if enc.assessment:
                diagnoses.append(enc.assessment)
            if enc.plan:
                # Basic medication parsing from plan
                for line in enc.plan.split("\n"):
                    if any(kw in line.lower() for kw in ["mg", "tablet", "daily", "oral", "capsule", "iv"]):
                        medications.append({"name": line.strip(), "encounter_id": enc.encounter_id})

        # 2. Vitals
        vit_stmt = select(VitalTelemetry).where(VitalTelemetry.patient_id == patient.id).order_by(desc(VitalTelemetry.created_at)).limit(10)
        vitals = list(db.execute(vit_stmt).scalars().all())

        # 3. CDS Alerts
        alr_stmt = select(ClinicalAlert).where(ClinicalAlert.patient_id == patient.id).order_by(desc(ClinicalAlert.created_at))
        alerts = list(db.execute(alr_stmt).scalars().all())

        # 4. Care Plans & Tasks
        cp_stmt = select(CarePlan).where(CarePlan.patient_id == patient.id).order_by(desc(CarePlan.created_at))
        care_plans = list(db.execute(cp_stmt).scalars().all())

        ct_stmt = select(CareTask).where(CareTask.patient_id == patient.id).order_by(desc(CareTask.created_at))
        care_tasks = list(db.execute(ct_stmt).scalars().all())

        # 5. Diagnostic Orders & Results
        ord_stmt = select(ClinicalOrder).where(ClinicalOrder.patient_id == patient.id).order_by(desc(ClinicalOrder.created_at))
        orders = list(db.execute(ord_stmt).scalars().all())

        res_stmt = select(DiagnosticResult).where(DiagnosticResult.patient_id == patient.id).order_by(desc(DiagnosticResult.created_at))
        results = list(db.execute(res_stmt).scalars().all())

        # 6. Quality Gaps
        qg_stmt = select(QualityMeasureGap).options(selectinload(QualityMeasureGap.measure)).where(QualityMeasureGap.patient_id == patient.id).order_by(desc(QualityMeasureGap.created_at))
        quality_gaps = list(db.execute(qg_stmt).scalars().all())


        # 7. RPM Observations & Alerts & PROMs
        rpm_obs_stmt = select(RPMObservation).where(RPMObservation.patient_id == patient.id).order_by(desc(RPMObservation.measured_at)).limit(10)
        rpm_observations = list(db.execute(rpm_obs_stmt).scalars().all())

        rpm_alr_stmt = select(RPMEscalationAlert).where(RPMEscalationAlert.patient_id == patient.id).order_by(desc(RPMEscalationAlert.created_at))
        rpm_alerts = list(db.execute(rpm_alr_stmt).scalars().all())

        prom_stmt = select(PROMResponse).where(PROMResponse.patient_id == patient.id).order_by(desc(PROMResponse.completed_at))
        prom_responses = list(db.execute(prom_stmt).scalars().all())

        # 8. Transitions & Discharges
        ho_stmt = select(ClinicalHandoff).where(ClinicalHandoff.patient_id == patient.id).order_by(desc(ClinicalHandoff.created_at))
        handoffs = list(db.execute(ho_stmt).scalars().all())

        dc_stmt = select(DischargeProtocol).where(DischargeProtocol.patient_id == patient.id).order_by(desc(DischargeProtocol.created_at))
        discharges = list(db.execute(dc_stmt).scalars().all())

        # 9. Trial Matches & Precision Oncology
        tm_stmt = select(TrialMatch).where(TrialMatch.patient_id == patient.id).order_by(desc(TrialMatch.created_at))
        trial_matches = list(db.execute(tm_stmt).scalars().all())

        pe_stmt = select(PrecisionTreatmentEligibility).where(PrecisionTreatmentEligibility.patient_id == patient.id).order_by(desc(PrecisionTreatmentEligibility.created_at))
        precision_eligibilities = list(db.execute(pe_stmt).scalars().all())

        context = {
            "patient_id": patient.patient_id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "gender": patient.gender.value if hasattr(patient.gender, "value") else str(patient.gender),
            "date_of_birth": str(patient.date_of_birth),
            "encounters": [
                {
                    "encounter_id": e.encounter_id,
                    "chief_complaint": e.chief_complaint,
                    "assessment": e.assessment,
                    "clinical_notes": e.clinical_notes,
                }
                for e in encounters
            ],
            "diagnoses": list(set(diagnoses)),
            "medications": medications,
            "vitals": [
                {
                    "vital_id": str(v.id),
                    "type": v.vital_type,
                    "value": v.value_numeric,
                    "unit": v.unit,
                }
                for v in vitals
            ],
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "title": a.title,
                    "message": a.explanation,
                    "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                    "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                }
                for a in alerts
            ],

            "care_plans": [{"plan_id": cp.plan_id, "title": cp.title, "status": cp.status} for cp in care_plans],
            "care_tasks": [
                {
                    "task_id": ct.task_id,
                    "title": ct.title,
                    "description": ct.description,
                    "status": ct.status,
                    "priority": ct.priority,
                    "assigned_role": ct.assigned_role,
                }
                for ct in care_tasks
            ],
            "orders": [
                {
                    "order_id": o.order_id,
                    "order_name": o.order_type,
                    "order_category": o.order_category,
                    "status": o.status,
                    "priority": o.priority,
                }
                for o in orders
            ],

            "results": [
                {
                    "result_id": r.result_id,
                    "test_name": r.test_name,
                    "value": r.numeric_value or r.findings_summary,
                    "unit": r.unit_of_measure or "",
                    "status": r.status,
                    "is_critical": r.abnormal_flag in ("panic_critical", "critical", "abnormal_high", "abnormal_low"),
                    "interpretation": r.findings_summary,
                }
                for r in results
            ],

            "quality_gaps": [
                {
                    "gap_id": qg.gap_id,
                    "measure_id": qg.measure.measure_id if qg.measure else str(qg.measure_id),
                    "measure_name": qg.measure.title if qg.measure else qg.gap_description,
                    "status": qg.status,
                    "recommended_action": qg.recommended_action,
                }
                for qg in quality_gaps
            ],

            "rpm_observations": [
                {
                    "observation_id": ro.observation_id,
                    "type": ro.observation_type,
                    "value": ro.numeric_value,
                    "unit": ro.unit_of_measure,
                    "classification": ro.classification,
                }
                for ro in rpm_observations
            ],
            "rpm_alerts": [
                {
                    "alert_id": ra.alert_id,
                    "reason": ra.escalation_reason,
                    "severity": ra.severity,
                    "status": ra.status,
                    "recommended_action": ra.clinical_action_taken or "Clinical review required.",
                }
                for ra in rpm_alerts
            ],
            "prom_responses": [
                {
                    "response_id": pr.response_id,
                    "survey_code": f"PROM-{pr.prom_id}",
                    "score": pr.calculated_score,
                    "severity": pr.severity_interpretation,
                    "safety_flag": bool(
                        (pr.answers_json and pr.answers_json.get("q9", 0) > 1)
                        or pr.severity_interpretation in ("severe", "moderate_severe")
                    ),
                }
                for pr in prom_responses
            ],
            "handoffs": [
                {
                    "handoff_id": h.handoff_id,
                    "handoff_type": h.handoff_type,
                    "illness_severity": h.illness_severity,
                    "status": h.status,
                    "action_items_text": h.summary,
                }
                for h in handoffs
            ],
            "discharges": [
                {
                    "discharge_id": d.discharge_id,
                    "status": d.status,
                    "destination": d.disposition,
                }
                for d in discharges
            ],

            "trial_matches": [
                {
                    "match_id": tm.match_id,
                    "trial_identifier": tm.trial_identifier,
                    "trial_title": tm.trial_title,
                    "match_status": tm.match_status,
                    "match_score": tm.match_score,
                    "overall_explanation": tm.overall_explanation,
                    "clinician_review_status": tm.clinician_review_status,
                }
                for tm in trial_matches
            ],
            "precision_eligibilities": [
                {
                    "eligibility_id": pe.eligibility_id,
                    "gene_symbol": pe.gene_symbol,
                    "variant_name": pe.variant_name,
                    "recommended_intervention": pe.recommended_intervention,
                    "drug_class": pe.drug_class,
                    "eligibility_status": pe.eligibility_status,
                    "evidence_source": pe.evidence_source,
                    "clinician_review_status": pe.clinician_review_status,
                }
                for pe in precision_eligibilities
            ],
        }
        return context

    # =========================================================================
    # 3. TRIGGER AGENT RUN
    # =========================================================================

    def trigger_agent_run(
        self,
        db: Session,
        patient_id_or_str: Any,
        agent_type: str = "master_orchestrator",
        initiated_by_user_id: Optional[int] = None,
        include_subagents: Optional[list[str]] = None,
    ) -> ClinicalAgentRun:
        """Execute a specialized or master clinical AI agent run for a patient."""
        self.seed_default_agents(db)
        patient = self._resolve_patient(db, patient_id_or_str)

        # Build context & context hash
        context = self.build_patient_context(db, patient.id)
        context_hash = _compute_sha256(context)

        # Create Run record
        count_stmt = select(ClinicalAgentRun).where(ClinicalAgentRun.patient_id == patient.id)
        current_count = len(db.execute(count_stmt).scalars().all())
        run_id = f"RUN-{patient.patient_id}-{current_count + 1:03d}"

        agent_run = ClinicalAgentRun(
            run_id=run_id,
            agent_type=agent_type,
            patient_id=patient.id,
            initiated_by_user_id=initiated_by_user_id,
            status="running",
            start_time=datetime.now(timezone.utc),
            input_context_snapshot_json=context,
            context_hash=context_hash,
            provenance_hash="pending",
        )
        db.add(agent_run)
        db.flush()

        try:
            # Execute deterministic multi-agent synthesis
            result = self.provider.orchestrate_master_run(
                patient_id=patient.patient_id, context=context, requested_subagents=include_subagents
            )

            agent_run.provenance_hash = result.get("provenance_hash", "none")
            agent_run.overall_summary = result.get("overall_summary")
            agent_run.end_time = datetime.now(timezone.utc)

            # Persist Recommendations & Evidence References
            has_pending_approvals = False
            for idx, r_data in enumerate(result.get("recommendations", [])):
                rec_id = f"REC-{run_id}-{idx + 1:02d}"
                action_cls = r_data.get("action_class", "RECOMMENDATION")
                appr_status = "pending_review" if action_cls in ("CLINICIAN_APPROVAL_REQUIRED", "HIGH_RISK") else "approved"
                if appr_status == "pending_review":
                    has_pending_approvals = True

                rec = ClinicalAgentRecommendation(
                    recommendation_id=rec_id,
                    run_id=agent_run.id,
                    patient_id=patient.id,
                    category=r_data.get("category", "general"),
                    title=r_data.get("title", "Clinical Recommendation"),
                    description=r_data.get("description", ""),
                    rationale=r_data.get("rationale", ""),
                    priority=r_data.get("priority", "medium"),
                    action_class=action_cls,
                    suggested_action_type=r_data.get("suggested_action_type"),
                    suggested_action_payload_json=r_data.get("suggested_action_payload_json"),
                    approval_status=appr_status,
                    provenance_hash=r_data.get("provenance_hash", _compute_sha256(r_data)),
                )
                db.add(rec)
                db.flush()

                # Add Evidence References
                for e_idx, e_data in enumerate(r_data.get("evidence_references", [])):
                    ev_id = f"EV-{rec_id}-{e_idx + 1:02d}"
                    ev = AgentEvidenceReference(
                        evidence_id=ev_id,
                        recommendation_id=rec.id,
                        entity_type=e_data.get("entity_type", "encounter"),
                        entity_identifier=str(e_data.get("entity_identifier", "UNKNOWN")),
                        title=e_data.get("title", "Evidence"),
                        excerpt=e_data.get("excerpt"),
                        confidence_score=e_data.get("confidence_score", 1.0),
                    )
                    db.add(ev)

            agent_run.status = "waiting_for_approval" if has_pending_approvals else "completed"
            db.commit()
            db.refresh(agent_run)
            return agent_run

        except Exception as exc:
            db.rollback()
            agent_run.status = "failed"
            agent_run.error_message = str(exc)
            agent_run.end_time = datetime.now(timezone.utc)
            db.commit()
            raise exc

    # =========================================================================
    # 4. QUERY RUNS & RECOMMENDATIONS
    # =========================================================================

    def list_agent_runs(
        self,
        db: Session,
        patient_id_or_str: Optional[Any] = None,
        status: Optional[str] = None,
        agent_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ClinicalAgentRun]:
        """List agent execution records with optional filtering."""
        stmt = (
            select(ClinicalAgentRun)
            .options(
                selectinload(ClinicalAgentRun.patient),
                selectinload(ClinicalAgentRun.initiated_by_user),
                selectinload(ClinicalAgentRun.recommendations),
            )
            .order_by(desc(ClinicalAgentRun.created_at))
        )
        if patient_id_or_str:
            patient = self._resolve_patient(db, patient_id_or_str)
            stmt = stmt.where(ClinicalAgentRun.patient_id == patient.id)
        if status:
            stmt = stmt.where(ClinicalAgentRun.status == status)
        if agent_type:
            stmt = stmt.where(ClinicalAgentRun.agent_type == agent_type)
        return list(db.execute(stmt.offset(skip).limit(limit)).scalars().all())

    def get_agent_run(self, db: Session, run_id_or_int: Any) -> Optional[ClinicalAgentRun]:
        """Retrieve detailed agent run with loaded recommendations and evidence references."""
        stmt = (
            select(ClinicalAgentRun)
            .options(
                selectinload(ClinicalAgentRun.patient),
                selectinload(ClinicalAgentRun.initiated_by_user),
                selectinload(ClinicalAgentRun.recommendations).selectinload(ClinicalAgentRecommendation.evidence_references),
                selectinload(ClinicalAgentRun.recommendations).selectinload(ClinicalAgentRecommendation.reviewed_by_user),
            )
        )
        if isinstance(run_id_or_int, int) or (isinstance(run_id_or_int, str) and run_id_or_int.isdigit()):
            stmt = stmt.where(ClinicalAgentRun.id == int(run_id_or_int))
        else:
            stmt = stmt.where(ClinicalAgentRun.run_id == str(run_id_or_int))
        return db.execute(stmt).scalar_one_or_none()

    def get_recommendation(self, db: Session, rec_id_or_int: Any) -> Optional[ClinicalAgentRecommendation]:
        """Retrieve recommendation record."""
        stmt = select(ClinicalAgentRecommendation).options(
            selectinload(ClinicalAgentRecommendation.evidence_references),
            selectinload(ClinicalAgentRecommendation.patient),
            selectinload(ClinicalAgentRecommendation.reviewed_by_user),
            selectinload(ClinicalAgentRecommendation.run),
        )
        if isinstance(rec_id_or_int, int) or (isinstance(rec_id_or_int, str) and rec_id_or_int.isdigit()):
            stmt = stmt.where(ClinicalAgentRecommendation.id == int(rec_id_or_int))
        else:
            stmt = stmt.where(ClinicalAgentRecommendation.recommendation_id == str(rec_id_or_int))
        return db.execute(stmt).scalar_one_or_none()

    # =========================================================================
    # 5. CLINICIAN REVIEW & ACTION EXECUTION
    # =========================================================================

    def review_recommendation(
        self,
        db: Session,
        rec_id_or_int: Any,
        approval_status: str,
        reviewed_by_user_id: int,
        review_notes: Optional[str] = None,
    ) -> ClinicalAgentRecommendation:
        """Record formal clinician sign-off (approval or rejection) on an agent recommendation."""
        rec = self.get_recommendation(db, rec_id_or_int)
        if not rec:
            raise ValueError(f"Recommendation '{rec_id_or_int}' was not found.")

        # Stale Check: verify that patient clinical context has not drastically changed
        current_context = self.build_patient_context(db, rec.patient_id)
        current_hash = _compute_sha256(current_context)
        if rec.run and rec.run.context_hash != current_hash:
            logger.warning(
                "Context hash drift detected during recommendation review for patient %s (run %s)",
                rec.patient_id,
                rec.run.run_id,
            )

        rec.approval_status = approval_status
        rec.reviewed_by_user_id = reviewed_by_user_id
        rec.reviewed_at = datetime.now(timezone.utc)
        rec.review_notes = review_notes

        # Check if all recommendations for the parent run are now reviewed
        if rec.run:
            run_recs = db.execute(
                select(ClinicalAgentRecommendation).where(ClinicalAgentRecommendation.run_id == rec.run_id)
            ).scalars().all()
            if all(r.approval_status != "pending_review" for r in run_recs):
                rec.run.status = "completed"

        db.commit()
        db.refresh(rec)
        return rec

    def execute_approved_recommendation(
        self, db: Session, rec_id_or_int: Any, executed_by_user_id: int
    ) -> ClinicalAgentRecommendation:
        """Execute an approved recommendation, creating corresponding CareTasks where applicable."""
        rec = self.get_recommendation(db, rec_id_or_int)
        if not rec:
            raise ValueError(f"Recommendation '{rec_id_or_int}' was not found.")
        if rec.approval_status != "approved":
            raise ValueError("Only approved recommendations may be executed.")

        execution_result = {}
        # If suggested action is care task creation, create the CareTask under patient's active care plan
        if rec.suggested_action_type == "complete_care_task" or rec.suggested_action_type == "create_care_task":
            active_plan = db.execute(
                select(CarePlan).where(CarePlan.patient_id == rec.patient_id).order_by(desc(CarePlan.created_at))
            ).scalars().first()
            if active_plan:
                count_stmt = select(CareTask).where(CareTask.care_plan_id == active_plan.id)
                current_task_count = len(db.execute(count_stmt).scalars().all())
                task_id = f"TASK-{active_plan.plan_id}-{current_task_count + 1:03d}"
                new_task = CareTask(
                    task_id=task_id,
                    care_plan_id=active_plan.id,
                    patient_id=rec.patient_id,
                    title=f"[AI Coordinated] {rec.title}",
                    description=rec.description,
                    task_type="clinical_followup",
                    status="pending",
                    priority="high" if rec.priority in ("urgent", "high") else "medium",
                    assigned_role="care_team",
                )
                db.add(new_task)
                execution_result = {"created_care_task_id": task_id, "care_plan_id": active_plan.plan_id}

        rec.execution_status = "completed"
        rec.executed_at = datetime.now(timezone.utc)
        rec.execution_result_json = execution_result

        db.commit()
        db.refresh(rec)
        return rec

    # =========================================================================
    # 6. CARE COORDINATION SYNTHESIS
    # =========================================================================

    def synthesize_care_coordination(
        self, db: Session, patient_id_or_str: Any, initiated_by_user_id: Optional[int] = None
    ) -> CareCoordinationSynthesisResponse:
        """Trigger one-click comprehensive multi-agent care coordination synthesis."""
        patient = self._resolve_patient(db, patient_id_or_str)
        run = self.trigger_agent_run(
            db,
            patient_id_or_str=patient.id,
            agent_type="master_orchestrator",
            initiated_by_user_id=initiated_by_user_id,
        )

        recs_out = []
        for r in run.recommendations:
            r_dto = ClinicalAgentRecommendationResponse.model_validate(r)
            r_dto.reviewed_by_name = r.reviewed_by_user.name if r.reviewed_by_user else None
            recs_out.append(r_dto)

        urgent_count = sum(1 for r in run.recommendations if r.priority == "urgent")
        high_count = sum(1 for r in run.recommendations if r.priority == "high")
        pending_count = sum(1 for r in run.recommendations if r.approval_status == "pending_review")

        return CareCoordinationSynthesisResponse(
            patient_id=patient.patient_id,
            patient_name=f"{patient.first_name} {patient.last_name}",
            run_id=run.run_id,
            status=AgentRunStatus(run.status),
            overall_summary=run.overall_summary or "Synthesis completed.",
            provenance_hash=run.provenance_hash,
            urgent_recommendations_count=urgent_count,
            high_recommendations_count=high_count,
            pending_approvals_count=pending_count,
            recommendations=recs_out,
        )


clinical_agent_service = ClinicalAgentService()
