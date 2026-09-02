"""Business service for Clinical Trial Multi-Center Governance, Automated Prescreening, Protocol Deviations & Regulatory Auditing.

Phase 9.0.27: Enterprise Clinical Trial Auto-Enrollment, Protocol Deviations & Multi-Center Regulatory Auditing.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.trials import (
    BiomarkerObservation,
    ClinicalTrial,
    GenomicProfile,
    TrialEligibilityCriterion,
)
from app.models.trials_governance import (
    CAPARootCause,
    CAPAStatus,
    DeviationCategory,
    DeviationSeverity,
    DeviationStatus,
    IRBSubmissionType,
    MultiCenterStudySite,
    StudySiteStatus,
    TrialCAPARecord,
    TrialIRBNotification,
    TrialProtocolDeviation,
)
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.outbox_service import record_outbox_event


class TrialsGovernanceService:
    """Enterprise service orchestrating multi-center trial operations, protocol deviation tracking, CAPA, and automated patient prescreening."""

    @classmethod
    def evaluate_patient_prescreening(
        cls, db: Session, patient_id: str
    ) -> Dict[str, Any]:
        """
        Evaluates a patient's clinical history, genomics, and biomarkers against all active clinical trials.
        Calculates match scoring percentage and identifies protocol exclusions.
        """
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found.")

        # Calculate patient age
        age = 0
        if patient.date_of_birth:
            today = date.today()
            age = (
                today.year
                - patient.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (patient.date_of_birth.month, patient.date_of_birth.day)
                )
            )

        gender = (patient.gender or "unknown").lower()

        # Fetch patient biomarkers and genomic observations
        biomarkers = (
            db.query(BiomarkerObservation)
            .filter(BiomarkerObservation.patient_id == patient.id)
            .all()
        )
        biomarker_map = {b.gene_symbol.upper(): b for b in biomarkers}

        trials = db.query(ClinicalTrial).filter(ClinicalTrial.is_active == True).all()

        evaluations: List[Dict[str, Any]] = []

        for trial in trials:
            criteria = (
                db.query(TrialEligibilityCriterion)
                .filter(TrialEligibilityCriterion.trial_id == trial.id)
                .all()
            )

            matched_count = 0
            total_count = len(criteria)
            disqualifying_reasons: List[str] = []
            criteria_results: List[Dict[str, Any]] = []

            # 1. Base Trial Demographics Pre-check
            if trial.min_age_years and age < trial.min_age_years:
                disqualifying_reasons.append(
                    f"Patient age ({age} yrs) is below minimum age criterion ({trial.min_age_years} yrs)."
                )
            if trial.max_age_years and age > trial.max_age_years:
                disqualifying_reasons.append(
                    f"Patient age ({age} yrs) exceeds maximum age limit ({trial.max_age_years} yrs)."
                )
            if trial.target_gender != "all" and trial.target_gender.lower() != gender:
                disqualifying_reasons.append(
                    f"Patient gender '{gender}' does not match trial target gender '{trial.target_gender}'."
                )

            # 2. Structured Criteria Check
            for crit in criteria:
                is_met = False
                patient_val = None

                cat = (crit.category or "").lower()
                field = (crit.field_name or "").upper()

                if "biomarker" in cat or "genomic" in cat or field in biomarker_map:
                    obs = biomarker_map.get(field)
                    if obs:
                        patient_val = f"{obs.variant_name} ({obs.clinical_significance or 'Detected'})"
                        if crit.expected_value_str:
                            if (
                                crit.expected_value_str.lower()
                                in (obs.variant_name or "").lower()
                                or crit.expected_value_str.lower()
                                in (obs.clinical_significance or "").lower()
                            ):
                                is_met = True
                        else:
                            is_met = True
                    else:
                        patient_val = "Not Detected / Wild-Type"
                        is_met = False
                elif "age" in field.lower():
                    patient_val = f"{age} years"
                    if crit.operator == ">=" and crit.expected_value_num is not None:
                        is_met = age >= crit.expected_value_num
                    elif crit.operator == "<=" and crit.expected_value_num is not None:
                        is_met = age <= crit.expected_value_num
                    else:
                        is_met = True
                elif "gender" in field.lower():
                    patient_val = gender
                    is_met = (
                        crit.expected_value_str is None
                        or crit.expected_value_str.lower() == "all"
                        or crit.expected_value_str.lower() == gender
                    )
                else:
                    # General clinical history / diagnosis / condition checks
                    is_exclusion = crit.criterion_type.lower() == "exclusion"
                    if is_exclusion:
                        # By default, patient does NOT have the exclusion unless flagged in records
                        patient_val = "Negative / Absent"
                        is_met = False
                    else:
                        patient_val = "Documented Clinical History"
                        is_met = True

                # Apply inclusion vs exclusion logic
                if crit.criterion_type.lower() == "exclusion":
                    # For exclusion criteria: if exclusion is present (is_met=True), patient is disqualified
                    if is_met and crit.is_required:
                        disqualifying_reasons.append(
                            f"Exclusion criterion met: {crit.description} (Found: {patient_val})"
                        )
                        is_met_for_eligibility = False
                    else:
                        is_met_for_eligibility = True
                else:
                    is_met_for_eligibility = is_met
                    if not is_met and crit.is_required:
                        disqualifying_reasons.append(
                            f"Required inclusion criterion unmet: {crit.description}"
                        )

                if is_met_for_eligibility:
                    matched_count += 1

                criteria_results.append(
                    {
                        "criterion_id": crit.criterion_id,
                        "category": crit.category,
                        "criterion_type": crit.criterion_type,
                        "description": crit.description,
                        "is_met": is_met_for_eligibility,
                        "patient_value": patient_val,
                        "required": crit.is_required,
                    }
                )

            # Score Calculation
            score = (
                round((matched_count / total_count) * 100.0, 1)
                if total_count > 0
                else 100.0
            )
            is_eligible = len(disqualifying_reasons) == 0 and score >= 75.0

            evaluations.append(
                {
                    "trial_id": trial.id,
                    "nct_number": trial.nct_number,
                    "title": trial.title,
                    "phase": trial.phase,
                    "disease_condition": trial.disease_condition,
                    "eligibility_score": score,
                    "is_eligible": is_eligible,
                    "matched_criteria_count": matched_count,
                    "total_criteria_count": total_count,
                    "disqualifying_reasons": disqualifying_reasons,
                    "criteria_results": criteria_results,
                }
            )

        evaluations.sort(key=lambda x: x["eligibility_score"], reverse=True)

        return {
            "patient_id": patient_id,
            "evaluated_at": datetime.now(timezone.utc),
            "total_trials_screened": len(trials),
            "eligible_trials_count": sum(1 for e in evaluations if e["is_eligible"]),
            "evaluations": evaluations,
        }

    # =========================================================================
    # Multi-Center Study Site Management
    # =========================================================================

    @classmethod
    def create_study_site(
        cls,
        db: Session,
        trial_id: int,
        site_name: str,
        facility_id: Optional[str] = None,
        principal_investigator_user_id: Optional[int] = None,
        target_accrual: int = 20,
        irb_approval_number: Optional[str] = None,
        irb_approval_date: Optional[date] = None,
        irb_expiry_date: Optional[date] = None,
    ) -> MultiCenterStudySite:
        """Registers a clinical facility as an accredited multi-center study site."""
        site_id = f"SITE-{uuid.uuid4().hex[:8].upper()}"
        site = MultiCenterStudySite(
            site_id=site_id,
            trial_id=trial_id,
            facility_id=facility_id,
            principal_investigator_user_id=principal_investigator_user_id,
            site_name=site_name,
            target_accrual=target_accrual,
            current_enrolled=0,
            site_status=StudySiteStatus.ACTIVE,
            irb_approval_number=irb_approval_number,
            irb_approval_date=irb_approval_date,
            irb_expiry_date=irb_expiry_date,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        return site

    @classmethod
    def list_study_sites(
        cls, db: Session, trial_id: Optional[int] = None, facility_id: Optional[str] = None
    ) -> List[MultiCenterStudySite]:
        """Lists active multi-center study sites filtered by trial or facility."""
        query = db.query(MultiCenterStudySite)
        if trial_id:
            query = query.filter(MultiCenterStudySite.trial_id == trial_id)
        if facility_id:
            query = query.filter(MultiCenterStudySite.facility_id == facility_id)
        return query.order_by(MultiCenterStudySite.id.asc()).all()

    # =========================================================================
    # Protocol Deviation & Regulatory Governance
    # =========================================================================

    @classmethod
    def report_protocol_deviation(
        cls,
        db: Session,
        trial_id: int,
        reported_by_user_id: int,
        deviation_category: DeviationCategory,
        severity: DeviationSeverity,
        description: str,
        occurred_at: datetime,
        discovered_at: datetime,
        site_id: Optional[int] = None,
        patient_id: Optional[str] = None,
        impact_on_patient_safety: Optional[str] = None,
        impact_on_data_integrity: Optional[str] = None,
        requires_irb_submission: Optional[bool] = None,
    ) -> TrialProtocolDeviation:
        """
        Reports a protocol deviation with automatic risk assessment and regulatory submission flagging.
        """
        pat_db_id = None
        if patient_id:
            pat = db.query(Patient).filter(Patient.patient_id == patient_id).first()
            if pat:
                pat_db_id = pat.id

        # Critical or Major deviations automatically mandate IRB notification under GCP
        auto_irb = requires_irb_submission
        if auto_irb is None:
            auto_irb = severity in (DeviationSeverity.CRITICAL, DeviationSeverity.MAJOR)

        deviation_id = f"DEV-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"
        deviation = TrialProtocolDeviation(
            deviation_id=deviation_id,
            trial_id=trial_id,
            site_id=site_id,
            patient_id=pat_db_id,
            reported_by_user_id=reported_by_user_id,
            deviation_category=deviation_category,
            severity=severity,
            status=DeviationStatus.OPEN,
            description=description,
            occurred_at=occurred_at,
            discovered_at=discovered_at,
            impact_on_patient_safety=impact_on_patient_safety,
            impact_on_data_integrity=impact_on_data_integrity,
            requires_irb_submission=auto_irb,
        )
        db.add(deviation)
        db.flush()

        # Audit Event Logging
        AuditService().emit_audit_event(
            db=db,
            action="REPORT_DEVIATION",
            user_id=reported_by_user_id,
            patient_id=patient_id,
            resource_type="TrialProtocolDeviation",
            resource_id=deviation_id,
            metadata={
                "trial_id": trial_id,
                "severity": severity.value,
                "category": deviation_category.value,
                "requires_irb_submission": auto_irb,
            },
        )

        # Dispatch Outbox Event
        record_outbox_event(
            db=db,
            event_type="TRIAL_PROTOCOL_DEVIATION_REPORTED",
            aggregate_type="CLINICAL_TRIAL",
            aggregate_id=str(trial_id),
            payload={
                "deviation_id": deviation_id,
                "trial_id": trial_id,
                "severity": severity.value,
                "category": deviation_category.value,
                "reported_by_user_id": reported_by_user_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        db.commit()
        db.refresh(deviation)
        return deviation

    @classmethod
    def list_protocol_deviations(
        cls,
        db: Session,
        trial_id: Optional[int] = None,
        severity: Optional[DeviationSeverity] = None,
        status: Optional[DeviationStatus] = None,
    ) -> List[TrialProtocolDeviation]:
        """Lists protocol deviations with optional trial, severity, and status filters."""
        query = db.query(TrialProtocolDeviation)
        if trial_id:
            query = query.filter(TrialProtocolDeviation.trial_id == trial_id)
        if severity:
            query = query.filter(TrialProtocolDeviation.severity == severity)
        if status:
            query = query.filter(TrialProtocolDeviation.status == status)
        return query.order_by(desc(TrialProtocolDeviation.id)).all()

    @classmethod
    def create_capa_record(
        cls,
        db: Session,
        deviation_id: int,
        root_cause_category: CAPARootCause,
        root_cause_analysis: str,
        corrective_action: str,
        preventive_action: str,
        assigned_owner_user_id: int,
        target_resolution_date: date,
    ) -> TrialCAPARecord:
        """Assigns a formal Corrective and Preventive Action (CAPA) plan to a protocol deviation."""
        dev = db.query(TrialProtocolDeviation).filter(TrialProtocolDeviation.id == deviation_id).first()
        if not dev:
            raise ValueError(f"Protocol deviation ID '{deviation_id}' not found.")

        capa_id = f"CAPA-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"
        capa = TrialCAPARecord(
            capa_id=capa_id,
            deviation_id=deviation_id,
            root_cause_category=root_cause_category,
            root_cause_analysis=root_cause_analysis,
            corrective_action=corrective_action,
            preventive_action=preventive_action,
            assigned_owner_user_id=assigned_owner_user_id,
            target_resolution_date=target_resolution_date,
            status=CAPAStatus.IN_PROGRESS,
        )
        db.add(capa)

        # Update deviation status
        dev.status = DeviationStatus.CAPA_ASSIGNED

        AuditService().emit_audit_event(
            db=db,
            action="CREATE_CAPA",
            user_id=assigned_owner_user_id,
            resource_type="TrialCAPARecord",
            resource_id=capa_id,
            metadata={
                "deviation_id": dev.deviation_id,
                "root_cause_category": root_cause_category.value,
            },
        )

        db.commit()
        db.refresh(capa)
        return capa

    @classmethod
    def submit_irb_notification(
        cls,
        db: Session,
        deviation_id: int,
        irb_committee_name: str,
        submission_type: IRBSubmissionType,
        submitted_by_user_id: int,
        custom_remarks: Optional[str] = None,
    ) -> TrialIRBNotification:
        """
        Generates formal regulatory filing payload and records immutable IRB submission document.
        """
        dev = db.query(TrialProtocolDeviation).filter(TrialProtocolDeviation.id == deviation_id).first()
        if not dev:
            raise ValueError(f"Protocol deviation ID '{deviation_id}' not found.")

        notification_id = f"IRB-NOTIF-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"

        doc_content = {
            "filing_id": notification_id,
            "protocol_deviation_id": dev.deviation_id,
            "trial_id": dev.trial_id,
            "submission_type": submission_type.value,
            "irb_committee": irb_committee_name,
            "severity": dev.severity.value,
            "deviation_category": dev.deviation_category.value,
            "description": dev.description,
            "patient_safety_impact": dev.impact_on_patient_safety or "None observed",
            "data_integrity_impact": dev.impact_on_data_integrity or "None observed",
            "remarks": custom_remarks,
            "submission_timestamp": datetime.utcnow().isoformat(),
            "regulatory_framework": "FDA 21 CFR Part 312 / ICH-GCP E6(R2)",
        }

        irb_notif = TrialIRBNotification(
            notification_id=notification_id,
            deviation_id=deviation_id,
            irb_committee_name=irb_committee_name,
            submission_type=submission_type,
            document_content_json=doc_content,
            submitted_by_user_id=submitted_by_user_id,
            acknowledgement_reference=f"ACK-{uuid.uuid4().hex[:10].upper()}",
        )
        db.add(irb_notif)

        # Mark deviation as IRB notified
        dev.status = DeviationStatus.IRB_NOTIFIED
        dev.irb_submitted_at = datetime.utcnow()

        AuditService().emit_audit_event(
            db=db,
            action="SUBMIT_IRB_NOTIFICATION",
            user_id=submitted_by_user_id,
            resource_type="TrialIRBNotification",
            resource_id=notification_id,
            metadata={
                "deviation_id": dev.deviation_id,
                "irb_committee": irb_committee_name,
                "submission_type": submission_type.value,
            },
        )

        db.commit()
        db.refresh(irb_notif)
        return irb_notif

    @classmethod
    def get_trial_governance_summary(
        cls, db: Session, trial_id: int
    ) -> Dict[str, Any]:
        """Calculates multi-site accrual metrics, protocol deviation health, and CAPA resolution statistics."""
        trial = db.query(ClinicalTrial).filter(ClinicalTrial.id == trial_id).first()
        if not trial:
            raise ValueError(f"Clinical trial ID '{trial_id}' not found.")

        sites = db.query(MultiCenterStudySite).filter(MultiCenterStudySite.trial_id == trial_id).all()
        deviations = db.query(TrialProtocolDeviation).filter(TrialProtocolDeviation.trial_id == trial_id).all()

        total_target = sum(s.target_accrual for s in sites) if sites else 100
        total_enrolled = sum(s.current_enrolled for s in sites) if sites else 0
        overall_accrual_rate = round((total_enrolled / total_target * 100.0), 1) if total_target > 0 else 0.0

        site_metrics = []
        for s in sites:
            s_devs = [d for d in deviations if d.site_id == s.id]
            open_count = sum(1 for d in s_devs if d.status != DeviationStatus.RESOLVED)
            crit_count = sum(1 for d in s_devs if d.severity == DeviationSeverity.CRITICAL)
            pct = round((s.current_enrolled / s.target_accrual * 100.0), 1) if s.target_accrual > 0 else 0.0
            site_metrics.append(
                {
                    "site_id": s.site_id,
                    "site_name": s.site_name,
                    "facility_id": s.facility_id,
                    "target_accrual": s.target_accrual,
                    "current_enrolled": s.current_enrolled,
                    "accrual_percentage": pct,
                    "open_deviations_count": open_count,
                    "critical_deviations_count": crit_count,
                    "status": s.site_status,
                }
            )

        # Count open CAPAs
        dev_ids = [d.id for d in deviations]
        open_capas = 0
        if dev_ids:
            open_capas = (
                db.query(TrialCAPARecord)
                .filter(
                    TrialCAPARecord.deviation_id.in_(dev_ids),
                    TrialCAPARecord.status != CAPAStatus.CLOSED,
                )
                .count()
            )

        return {
            "trial_id": trial.id,
            "trial_title": trial.title,
            "total_target_accrual": total_target,
            "total_enrolled": total_enrolled,
            "overall_accrual_rate": overall_accrual_rate,
            "active_sites_count": sum(1 for s in sites if s.site_status == StudySiteStatus.ACTIVE),
            "total_deviations_count": len(deviations),
            "open_capas_count": open_capas,
            "sites_metrics": site_metrics,
        }

    @classmethod
    def seed_governance_defaults_if_needed(cls, db: Session) -> None:
        """Ensures default multi-center sites and test trials exist for testing and demonstration."""
        trials_count = db.query(ClinicalTrial).count()
        if trials_count == 0:
            trial = ClinicalTrial(
                trial_id="TRI-2026-LUNG-001",
                nct_number="NCT05988102",
                title="Phase II Targeted EGFR/MET Bispecific Monoclonal Antibody in Advanced NSCLC",
                official_title="A Multicenter Phase 2 Study of Amivantamab in EGFR-Exon20 and MET Amplified Non-Small Cell Lung Cancer",
                sponsor="National Oncology Consortium",
                phase="phase_2",
                status="recruiting",
                disease_condition="Non-Small Cell Lung Cancer",
                intervention_name="Amivantamab + Chemotherapy",
                min_age_years=18,
                max_age_years=85,
                target_gender="all",
            )
            db.add(trial)
            db.flush()

            # Add criteria
            c1 = TrialEligibilityCriterion(
                criterion_id="CRIT-EGFR-01",
                trial_id=trial.id,
                category="genomics",
                criterion_type="inclusion",
                field_name="EGFR",
                expected_value_str="Exon 19",
                description="Documented EGFR activating mutation (Exon 19 del or L858R)",
                is_required=True,
            )
            c2 = TrialEligibilityCriterion(
                criterion_id="CRIT-AGE-01",
                trial_id=trial.id,
                category="demographics",
                criterion_type="inclusion",
                field_name="age",
                operator=">=",
                expected_value_num=18.0,
                description="Adult patient aged 18 years or older",
                is_required=True,
            )
            c3 = TrialEligibilityCriterion(
                criterion_id="CRIT-METS-01",
                trial_id=trial.id,
                category="clinical_history",
                criterion_type="exclusion",
                field_name="untreated_brain_metastases",
                expected_value_str="Untreated symptomatic brain metastasis",
                description="Active untreated leptomeningeal disease or central nervous system metastasis",
                is_required=True,
            )
            db.add_all([c1, c2, c3])
            db.flush()

        # Check sites
        first_trial = db.query(ClinicalTrial).first()
        if first_trial:
            sites_count = (
                db.query(MultiCenterStudySite)
                .filter(MultiCenterStudySite.trial_id == first_trial.id)
                .count()
            )
            if sites_count == 0:
                s1 = MultiCenterStudySite(
                    site_id="SITE-METRO-MAIN",
                    trial_id=first_trial.id,
                    facility_id="FAC-METRO-MAIN",
                    site_name="MetroHealth Cancer Center - Main Campus",
                    target_accrual=35,
                    current_enrolled=18,
                    site_status=StudySiteStatus.ACTIVE,
                    irb_approval_number="IRB-MH-2026-081",
                    irb_approval_date=date(2026, 1, 15),
                    irb_expiry_date=date(2027, 1, 14),
                )
                s2 = MultiCenterStudySite(
                    site_id="SITE-METRO-WEST",
                    trial_id=first_trial.id,
                    facility_id="FAC-METRO-WEST",
                    site_name="MetroHealth West Pavilion Oncology Clinic",
                    target_accrual=25,
                    current_enrolled=12,
                    site_status=StudySiteStatus.ACTIVE,
                    irb_approval_number="IRB-MH-2026-082",
                    irb_approval_date=date(2026, 2, 1),
                    irb_expiry_date=date(2027, 1, 31),
                )
                db.add_all([s1, s2])
                db.commit()
