"""Medical Imaging & Radiology Service.

Phase 9.0.18: Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow.
"""

from datetime import datetime, timezone
import hashlib
import json
import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.imaging_provider import MockImagingAIProvider, _compute_sha256, _sanitize_untrusted_text
from app.models.alert import ClinicalAlert
from app.models.encounter import Encounter
from app.models.imaging import ImagingAsset, ImagingFinding, ImagingStudy, RadiologyReport
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.models.vital import VitalTelemetry
from app.schemas.alert import AlertSeverity, AlertStatus
from app.schemas.imaging import (
    FindingReviewStatus,
    ImagingAssetCreate,
    ImagingStudyCreate,
    ImagingStudyUpdate,
    RadiologyReportCreate,
    RadiologyReportUpdate,
    ReportAmendRequest,
    ReportFinalizeRequest,
    ReportStatus,
)


class ImagingService:
    """Orchestrates clinical imaging study ingestion, AI analysis, reporting, and review."""

    def __init__(self, ai_provider: Optional[MockImagingAIProvider] = None):
        self.ai_provider = ai_provider or MockImagingAIProvider()

    # =========================================================================
    # 1. IMAGING STUDY LIFECYCLE
    # =========================================================================

    def create_study(
        self,
        db: Session,
        data: ImagingStudyCreate,
        current_user: User,
    ) -> ImagingStudy:
        """Create a new clinical imaging study record."""
        # Resolve patient
        patient = self._resolve_patient(db, data.patient_id)

        # Generate unique study_id and accession_number if not provided
        study_id = f"STU-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        accession_number = data.accession_number or f"ACC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        study_datetime = data.study_datetime or datetime.now(timezone.utc)

        provenance_payload = {
            "study_id": study_id,
            "patient_id": patient.id,
            "accession_number": accession_number,
            "modality": data.modality.value,
            "body_site": data.body_site.value,
            "created_by": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        provenance_hash = _compute_sha256(provenance_payload)

        study = ImagingStudy(
            study_id=study_id,
            patient_id=patient.id,
            encounter_id=data.encounter_id,
            order_id=data.order_id,
            modality=data.modality.value,
            body_site=data.body_site.value,
            study_description=_sanitize_untrusted_text(data.study_description),
            accession_number=accession_number,
            study_datetime=study_datetime,
            performing_department=data.performing_department or "Radiology & Diagnostic Imaging",
            referring_provider=data.referring_provider,
            status=data.status.value,
            source=data.source or "PACS_IMPORT",
            external_identifier=data.external_identifier,
            metadata_json=data.metadata_json,
            provenance_hash=provenance_hash,
        )

        db.add(study)
        db.commit()
        db.refresh(study)
        return study

    def get_study(
        self,
        db: Session,
        study_id_or_num: str | int,
        patient_id: Optional[int] = None,
    ) -> ImagingStudy:
        """Retrieve an ImagingStudy by study_id or numeric ID with patient scoping."""
        stmt = (
            select(ImagingStudy)
            .options(
                selectinload(ImagingStudy.patient),
                selectinload(ImagingStudy.encounter),
                selectinload(ImagingStudy.order),
                selectinload(ImagingStudy.assets),
                selectinload(ImagingStudy.findings),
                selectinload(ImagingStudy.reports),
            )
        )
        if isinstance(study_id_or_num, int) or str(study_id_or_num).isdigit():
            stmt = stmt.where(ImagingStudy.id == int(study_id_or_num))
        else:
            stmt = stmt.where(ImagingStudy.study_id == str(study_id_or_num))

        if patient_id is not None:
            stmt = stmt.where(ImagingStudy.patient_id == patient_id)

        study = db.execute(stmt).scalar_one_or_none()
        if not study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imaging study '{study_id_or_num}' not found",
            )
        return study

    def list_studies(
        self,
        db: Session,
        patient_id: Optional[str | int] = None,
        modality: Optional[str] = None,
        study_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[ImagingStudy], int]:
        """List imaging studies with optional filtering."""
        stmt = (
            select(ImagingStudy)
            .options(
                selectinload(ImagingStudy.patient),
                selectinload(ImagingStudy.assets),
                selectinload(ImagingStudy.findings),
                selectinload(ImagingStudy.reports),
            )
            .order_by(desc(ImagingStudy.study_datetime))
        )

        if patient_id is not None:
            patient = self._resolve_patient(db, patient_id)
            stmt = stmt.where(ImagingStudy.patient_id == patient.id)

        if modality:
            stmt = stmt.where(ImagingStudy.modality == modality.upper())

        if study_status:
            stmt = stmt.where(ImagingStudy.status == study_status.upper())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar() or 0

        studies = list(db.execute(stmt.offset(skip).limit(limit)).scalars().all())
        return studies, total

    # =========================================================================
    # 2. IMAGE ASSETS & SERIES MANAGEMENT
    # =========================================================================

    def add_asset(
        self,
        db: Session,
        study_id: str,
        data: ImagingAssetCreate,
        current_user: User,
    ) -> ImagingAsset:
        """Register an image/series asset under an imaging study."""
        study = self.get_study(db, study_id)

        asset_id = f"AST-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        provenance_payload = {
            "asset_id": asset_id,
            "study_id": study.id,
            "storage_path": data.storage_path,
            "modality": data.modality.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        provenance_hash = _compute_sha256(provenance_payload)

        asset = ImagingAsset(
            asset_id=asset_id,
            study_id=study.id,
            series_instance_uid=data.series_instance_uid,
            sop_instance_uid=data.sop_instance_uid,
            series_number=data.series_number or 1,
            instance_number=data.instance_number or 1,
            series_description=_sanitize_untrusted_text(data.series_description),
            modality=data.modality.value,
            body_site=data.body_site.value if data.body_site else study.body_site,
            mime_type=data.mime_type,
            file_size_bytes=data.file_size_bytes,
            storage_path=data.storage_path,
            thumbnail_storage_path=data.thumbnail_storage_path,
            image_dimensions=data.image_dimensions,
            dicom_metadata_json=data.dicom_metadata_json,
            provenance_hash=provenance_hash,
        )

        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    def list_assets(
        self,
        db: Session,
        study_id: str,
    ) -> list[ImagingAsset]:
        """List all registered assets for a study."""
        study = self.get_study(db, study_id)
        stmt = (
            select(ImagingAsset)
            .where(ImagingAsset.study_id == study.id)
            .order_by(ImagingAsset.series_number, ImagingAsset.instance_number)
        )
        return list(db.execute(stmt).scalars().all())

    # =========================================================================
    # 3. MULTIMODAL CONTEXT & AI INTERPRETATION
    # =========================================================================

    def build_multimodal_context(
        self,
        db: Session,
        patient_id: int,
        study_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Aggregate longitudinal patient diagnostic facts into a structured multimodal context."""
        patient = db.get(Patient, patient_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        # 1. Encounters & Diagnoses
        enc_stmt = select(Encounter).where(Encounter.patient_id == patient.id).order_by(desc(Encounter.created_at)).limit(5)
        encounters = list(db.execute(enc_stmt).scalars().all())

        diagnoses: list[str] = []
        medications: list[str] = []
        allergies: list[str] = []
        for e in encounters:
            if e.assessment:
                for line in e.assessment.split("\n"):
                    cleaned = line.strip()
                    if cleaned and cleaned not in diagnoses:
                        diagnoses.append(cleaned)
            if e.plan:
                for line in e.plan.split("\n"):
                    cleaned = line.strip()
                    if cleaned and cleaned not in medications:
                        medications.append(cleaned)

        # 2. Recent Vitals
        vit_stmt = select(VitalTelemetry).where(VitalTelemetry.patient_id == patient.id).order_by(desc(VitalTelemetry.measured_at)).limit(5)
        vitals = list(db.execute(vit_stmt).scalars().all())
        vitals_list = [
            {
                "heart_rate": v.heart_rate,
                "systolic_bp": v.systolic_bp,
                "diastolic_bp": v.diastolic_bp,
                "spo2": v.spo2,
                "temperature": v.temperature,
                "measured_at": v.measured_at.isoformat() if v.measured_at else None,
            }
            for v in vitals
        ]

        # 3. Active Alerts
        alr_stmt = select(ClinicalAlert).where(ClinicalAlert.patient_id == patient.id, ClinicalAlert.status == AlertStatus.ACTIVE)
        alerts = list(db.execute(alr_stmt).scalars().all())
        alerts_list = [{"title": a.title, "severity": a.severity.value, "type": a.alert_type} for a in alerts]

        # 4. Diagnostic Lab Results
        res_stmt = select(DiagnosticResult).where(DiagnosticResult.patient_id == patient.id).order_by(desc(DiagnosticResult.resulted_at)).limit(5)
        results = list(db.execute(res_stmt).scalars().all())
        labs_list = [
            {
                "test_name": r.test_name,
                "value": r.numeric_value or r.findings_summary,
                "unit": r.unit_of_measure,
                "flag": r.abnormal_flag,
            }
            for r in results
        ]

        # 5. Previous Imaging Studies
        prior_stmt = (
            select(ImagingStudy)
            .where(ImagingStudy.patient_id == patient.id)
            .order_by(desc(ImagingStudy.study_datetime))
        )
        if study_id:
            prior_stmt = prior_stmt.where(ImagingStudy.id != study_id)
        prior_studies = list(db.execute(prior_stmt.limit(5)).scalars().all())
        prior_list = [
            {
                "study_id": p.study_id,
                "modality": p.modality,
                "body_site": p.body_site,
                "study_datetime": p.study_datetime.isoformat() if p.study_datetime else None,
                "description": p.study_description,
            }
            for p in prior_studies
        ]

        # Calculate patient age
        age = 0
        if patient.date_of_birth:
            age = (datetime.now(timezone.utc).date() - patient.date_of_birth).days // 365

        return {
            "patient_id": patient.patient_id,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "age_years": age,
            "gender": patient.gender.value if hasattr(patient.gender, "value") else str(patient.gender),
            "active_diagnoses": diagnoses,
            "active_medications": medications,
            "allergies": allergies,
            "recent_vitals": vitals_list,
            "active_alerts": alerts_list,
            "relevant_lab_results": labs_list,
            "previous_studies": prior_list,
        }

    def run_ai_analysis(
        self,
        db: Session,
        study_id: str,
        current_user: User,
    ) -> dict[str, Any]:
        """Execute multimodal AI interpretation, persist findings, draft report, and flag critical alerts."""
        study = self.get_study(db, study_id)

        # 1. Build multimodal context
        multimodal_context = self.build_multimodal_context(db, study.patient_id, study.id)
        multimodal_context["clinical_indication"] = study.study_description
        multimodal_context["modality"] = study.modality
        multimodal_context["body_site"] = study.body_site


        study_data = {
            "study_id": study.study_id,
            "modality": study.modality,
            "body_site": study.body_site,
            "study_description": study.study_description,
            "accession_number": study.accession_number,
        }

        # 2. Run deterministic AI analysis
        raw_output = self.ai_provider.interpret_study(study_data, multimodal_context)

        # 3. Persist ImagingFinding records
        saved_findings: list[ImagingFinding] = []
        has_critical = False
        critical_descriptions: list[str] = []

        for f_dict in raw_output.get("findings", []):
            if f_dict.get("is_critical"):
                has_critical = True
                critical_descriptions.append(f_dict.get("description", "Critical finding"))

            finding = ImagingFinding(
                finding_id=f_dict["finding_id"],
                study_id=study.id,
                patient_id=study.patient_id,
                finding_type=f_dict["finding_type"],
                anatomical_location=f_dict["anatomical_location"],
                laterality=f_dict.get("laterality", "NOT_APPLICABLE"),
                severity=f_dict.get("severity", "NORMAL"),
                confidence_score=f_dict.get("confidence_score", 1.0),
                is_critical=f_dict.get("is_critical", False),
                finding_nature=f_dict.get("finding_nature", "AI_GENERATED_FINDING"),
                description=f_dict["description"],
                recommendation=f_dict["recommendation"],
                bounding_box_json=f_dict.get("bounding_box_json"),
                clinician_review_status="pending_review",
                provenance_hash=f_dict["provenance_hash"],
            )
            db.add(finding)
            saved_findings.append(finding)

        # 4. Generate or Update Draft RadiologyReport
        draft_rep_data = raw_output.get("draft_report", {})
        existing_report = (
            db.execute(select(RadiologyReport).where(RadiologyReport.study_id == study.id))
            .scalars()
            .first()
        )

        report_id = existing_report.report_id if existing_report else f"RAD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        if existing_report:
            existing_report.status = ReportStatus.AI_ASSISTED.value
            existing_report.clinical_indication = draft_rep_data.get("clinical_indication", study.study_description)
            existing_report.technique = draft_rep_data.get("technique", "")
            existing_report.comparison_studies = draft_rep_data.get("comparison_studies", "None available.")
            existing_report.findings = draft_rep_data.get("findings", "")
            existing_report.impression = draft_rep_data.get("impression", "")
            existing_report.recommendations = draft_rep_data.get("recommendations", "")
            existing_report.critical_findings_summary = draft_rep_data.get("critical_findings_summary")
            existing_report.is_critical = draft_rep_data.get("is_critical", False)
            existing_report.ai_assistance_metadata_json = draft_rep_data.get("ai_assistance_metadata_json")
            existing_report.provenance_hash = draft_rep_data.get("provenance_hash", "")
            report = existing_report
        else:
            report = RadiologyReport(
                report_id=report_id,
                study_id=study.id,
                patient_id=study.patient_id,
                encounter_id=study.encounter_id,
                order_id=study.order_id,
                status=ReportStatus.AI_ASSISTED.value,
                clinical_indication=draft_rep_data.get("clinical_indication", study.study_description),
                technique=draft_rep_data.get("technique", ""),
                comparison_studies=draft_rep_data.get("comparison_studies", "None available."),
                findings=draft_rep_data.get("findings", ""),
                impression=draft_rep_data.get("impression", ""),
                recommendations=draft_rep_data.get("recommendations", ""),
                critical_findings_summary=draft_rep_data.get("critical_findings_summary"),
                is_critical=draft_rep_data.get("is_critical", False),
                ai_assistance_metadata_json=draft_rep_data.get("ai_assistance_metadata_json"),
                author_user_id=current_user.id,
                provenance_hash=draft_rep_data.get("provenance_hash", ""),
            )
            db.add(report)

        # 5. Escalate Critical Finding as ClinicalAlert
        if has_critical:
            crit_alert_id = f"ALT-IMG-{uuid.uuid4().hex[:8].upper()}"
            alert = ClinicalAlert(
                alert_id=crit_alert_id,
                patient_id=study.patient_id,
                alert_type="imaging_critical_finding",
                title=f"Critical Imaging Finding: {study.modality} {study.body_site}",
                explanation=f"POTENTIALLY CRITICAL AI-ASSISTED FINDING — REQUIRES IMMEDIATE CLINICIAN REVIEW. Study {study.study_id} ({study.study_description}): {'; '.join(critical_descriptions)}",
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.ACTIVE,
            )
            db.add(alert)

        # Update study status
        study.status = "COMPLETED"
        db.commit()

        # Reload study to get updated relationships
        db.refresh(study)

        return {
            "study_id": study.study_id,
            "status": "COMPLETED",
            "findings_count": len(saved_findings),
            "critical_findings_count": len(critical_descriptions),
            "findings": saved_findings,
            "draft_report": report,
            "multimodal_context": multimodal_context,
            "provenance_hash": raw_output.get("provenance_hash", ""),
            "evaluated_at": datetime.now(timezone.utc),
        }

    # =========================================================================
    # 4. RADIOLOGY REPORT REVIEW, SIGN-OFF & AMENDMENT WORKFLOW
    # =========================================================================

    def get_report(
        self,
        db: Session,
        report_id: str,
    ) -> RadiologyReport:
        """Retrieve a RadiologyReport by report_id."""
        stmt = (
            select(RadiologyReport)
            .options(
                selectinload(RadiologyReport.study),
                selectinload(RadiologyReport.patient),
                selectinload(RadiologyReport.author_user),
                selectinload(RadiologyReport.signed_by_user),
            )
            .where(RadiologyReport.report_id == report_id)
        )
        report = db.execute(stmt).scalar_one_or_none()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Radiology report '{report_id}' not found",
            )
        return report

    def update_draft_report(
        self,
        db: Session,
        report_id: str,
        data: RadiologyReportUpdate,
        current_user: User,
    ) -> RadiologyReport:
        """Update draft report content before finalization."""
        report = self.get_report(db, report_id)

        if report.status in (ReportStatus.FINALIZED.value, ReportStatus.AMENDED.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Finalized or amended radiology reports cannot be edited directly. Use the amendment workflow.",
            )

        if data.clinical_indication is not None:
            report.clinical_indication = _sanitize_untrusted_text(data.clinical_indication)
        if data.technique is not None:
            report.technique = _sanitize_untrusted_text(data.technique)
        if data.comparison_studies is not None:
            report.comparison_studies = _sanitize_untrusted_text(data.comparison_studies)
        if data.findings is not None:
            report.findings = _sanitize_untrusted_text(data.findings)
        if data.impression is not None:
            report.impression = _sanitize_untrusted_text(data.impression)
        if data.recommendations is not None:
            report.recommendations = _sanitize_untrusted_text(data.recommendations)
        if data.critical_findings_summary is not None:
            report.critical_findings_summary = _sanitize_untrusted_text(data.critical_findings_summary)
        if data.is_critical is not None:
            report.is_critical = data.is_critical

        report.author_user_id = current_user.id
        db.commit()
        db.refresh(report)
        return report

    def submit_report_for_review(
        self,
        db: Session,
        report_id: str,
        current_user: User,
    ) -> RadiologyReport:
        """Submit a draft report to the radiologist review queue."""
        report = self.get_report(db, report_id)
        if report.status == ReportStatus.FINALIZED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report is already finalized.",
            )
        report.status = ReportStatus.RADIOLOGIST_REVIEW.value
        db.commit()
        db.refresh(report)
        return report

    def finalize_report(
        self,
        db: Session,
        report_id: str,
        data: ReportFinalizeRequest,
        current_user: User,
    ) -> RadiologyReport:
        """Sign off and finalize a radiology report (requires authorized DOCTOR/ADMIN)."""
        if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only licensed physicians or authorized administrators can sign and finalize radiology reports.",
            )

        report = self.get_report(db, report_id)

        if report.status == ReportStatus.FINALIZED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Radiology report is already finalized.",
            )

        report.status = ReportStatus.FINALIZED.value
        report.signed_by_user_id = current_user.id
        report.signed_at = datetime.now(timezone.utc)

        # Update provenance with signature audit
        sig_provenance = {
            "report_id": report.report_id,
            "signed_by_user_id": current_user.id,
            "signed_at": report.signed_at.isoformat(),
            "signature_notes": data.signature_notes,
            "previous_hash": report.provenance_hash,
        }
        report.provenance_hash = _compute_sha256(sig_provenance)

        # Also update parent study status to FINAL
        if report.study:
            report.study.status = "FINAL"

        db.commit()
        db.refresh(report)
        return report

    def amend_report(
        self,
        db: Session,
        report_id: str,
        data: ReportAmendRequest,
        current_user: User,
    ) -> RadiologyReport:
        """Create an amended version of a previously finalized radiology report."""
        if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only licensed physicians can issue report amendments.",
            )

        original = self.get_report(db, report_id)

        # Mark original as AMENDED if currently finalized
        if original.status == ReportStatus.FINALIZED.value:
            original.status = ReportStatus.AMENDED.value

        new_report_id = f"RAD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        amended_findings = _sanitize_untrusted_text(data.amended_findings) if data.amended_findings else original.findings
        amended_impression = _sanitize_untrusted_text(data.amended_impression) if data.amended_impression else original.impression
        amended_recommendations = _sanitize_untrusted_text(data.amended_recommendations) if data.amended_recommendations else original.recommendations

        provenance_payload = {
            "amended_report_id": new_report_id,
            "original_report_id": original.report_id,
            "amendment_reason": data.amendment_reason,
            "signed_by_user_id": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        provenance_hash = _compute_sha256(provenance_payload)

        amended_report = RadiologyReport(
            report_id=new_report_id,
            study_id=original.study_id,
            patient_id=original.patient_id,
            encounter_id=original.encounter_id,
            order_id=original.order_id,
            status=ReportStatus.FINALIZED.value,
            clinical_indication=original.clinical_indication,
            technique=original.technique,
            comparison_studies=original.comparison_studies,
            findings=amended_findings,
            impression=amended_impression,
            recommendations=amended_recommendations,
            critical_findings_summary=original.critical_findings_summary,
            is_critical=original.is_critical,
            ai_assistance_metadata_json=original.ai_assistance_metadata_json,
            author_user_id=original.author_user_id,
            signed_by_user_id=current_user.id,
            signed_at=datetime.now(timezone.utc),
            amendment_reason=_sanitize_untrusted_text(data.amendment_reason),
            amended_from_report_id=original.id,
            provenance_hash=provenance_hash,
        )

        db.add(amended_report)
        db.commit()
        db.refresh(amended_report)
        return amended_report

    # =========================================================================
    # 5. FINDING REVIEW & TIMELINE
    # =========================================================================

    def review_finding(
        self,
        db: Session,
        finding_id: str,
        review_status: FindingReviewStatus,
        review_notes: Optional[str],
        current_user: User,
    ) -> ImagingFinding:
        """Review and confirm/reject an individual AI-assisted image finding."""
        stmt = select(ImagingFinding).where(ImagingFinding.finding_id == finding_id)
        finding = db.execute(stmt).scalar_one_or_none()
        if not finding:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding '{finding_id}' not found")

        finding.clinician_review_status = review_status.value
        finding.review_notes = _sanitize_untrusted_text(review_notes)
        finding.reviewed_by_user_id = current_user.id
        finding.reviewed_at = datetime.now(timezone.utc)
        if review_status == FindingReviewStatus.CONFIRMED:
            finding.finding_nature = "CLINICIAN_CONFIRMED_FINDING"

        db.commit()
        db.refresh(finding)
        return finding

    def get_imaging_timeline(
        self,
        db: Session,
        patient_id_or_ident: str | int,
    ) -> list[dict[str, Any]]:
        """Retrieve longitudinal imaging timeline for a patient."""
        patient = self._resolve_patient(db, patient_id_or_ident)

        studies, _ = self.list_studies(db, patient_id=patient.id, limit=200)

        timeline_items: list[dict[str, Any]] = []
        for s in studies:
            has_crit = any(f.is_critical for f in s.findings)
            primary_rep = s.reports[0] if s.reports else None
            timeline_items.append({
                "event_id": f"EVT-IMG-{s.id}",
                "study_id": s.study_id,
                "study_datetime": s.study_datetime,
                "modality": s.modality,
                "body_site": s.body_site,
                "description": s.study_description,
                "status": s.status,
                "accession_number": s.accession_number,
                "findings_count": len(s.findings),
                "has_critical": has_crit,
                "report_id": primary_rep.report_id if primary_rep else None,
                "report_status": primary_rep.status if primary_rep else None,
            })

        return timeline_items

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _resolve_patient(self, db: Session, patient_id_or_ident: str | int) -> Patient:
        """Resolve a Patient ORM entity by business identifier or primary key."""
        if isinstance(patient_id_or_ident, int) or str(patient_id_or_ident).isdigit():
            patient = db.get(Patient, int(patient_id_or_ident))
            if patient:
                return patient

        stmt = select(Patient).where(Patient.patient_id == str(patient_id_or_ident))
        patient = db.execute(stmt).scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient '{patient_id_or_ident}' not found",
            )
        return patient


imaging_service = ImagingService()
