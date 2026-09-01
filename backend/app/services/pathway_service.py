"""Regional Multi-Hospital Clinical Pathways & Care Plan Synchronization Service."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from app.core.tenant_context import verify_cross_facility_transfer_authorization
from app.models.outbox import OutboxEvent
from app.models.pathway import (
    PatientPathwayEnrollment,
    PatientPathwayStageEvent,
    PathwayMilestone,
    PathwayStage,
    RegionalClinicalPathway,
)
from app.models.patient import Patient
from app.models.user import User
from app.schemas.pathway import (
    PathwayMilestoneCreate,
    PathwayMilestoneResponse,
    PathwayStageCreate,
    PathwayStageResponse,
    PatientPathwayEnrollmentResponse,
    PatientPathwayEventResponse,
    RegionalPathwayCreate,
    RegionalPathwayResponse,
)
from app.services.audit_service import audit_service


class PathwayService:
    """Orchestrates multi-facility clinical pathways, stage transitions, and cross-hospital milestones."""

    def create_pathway(
        self,
        db: Session,
        pathway_in: RegionalPathwayCreate,
        user_id: Optional[int] = None,
    ) -> RegionalPathwayResponse:
        """Define a standardized regional clinical pathway with ordered stages and milestones."""
        pathway_id = f"PATH-{uuid.uuid4().hex[:10].upper()}"

        pathway = RegionalClinicalPathway(
            pathway_id=pathway_id,
            code=pathway_in.code.upper().strip(),
            name=pathway_in.name.strip(),
            category=pathway_in.category.strip(),
            description=pathway_in.description.strip(),
            target_duration_hours=pathway_in.target_duration_hours,
            is_active=True,
        )
        db.add(pathway)
        db.flush()

        for st_idx, st_in in enumerate(pathway_in.stages):
            stage_id = f"STG-{uuid.uuid4().hex[:10].upper()}"
            stage = PathwayStage(
                stage_id=stage_id,
                pathway_id=pathway.pathway_id,
                sequence_order=st_in.sequence_order or (st_idx + 1),
                name=st_in.name,
                description=st_in.description,
                assigned_facility_id=st_in.assigned_facility_id,
                target_duration_minutes=st_in.target_duration_minutes,
                required_role=st_in.required_role,
                clinical_criteria_json=st_in.clinical_criteria_json,
                is_mandatory=st_in.is_mandatory,
            )
            db.add(stage)
            db.flush()

            for ms_in in st_in.milestones:
                milestone_id = f"MS-{uuid.uuid4().hex[:10].upper()}"
                milestone = PathwayMilestone(
                    milestone_id=milestone_id,
                    stage_id=stage.stage_id,
                    name=ms_in.name,
                    criteria_code=ms_in.criteria_code,
                    expected_order_type=ms_in.expected_order_type,
                    is_critical=ms_in.is_critical,
                )
                db.add(milestone)

        db.commit()
        db.refresh(pathway)

        audit_service.emit_audit_event(
            db=db,
            user_id=user_id or 1,
            action="REGIONAL_PATHWAY_CREATED",
            resource_type="RegionalClinicalPathway",
            resource_id=pathway.pathway_id,
            metadata={
                "code": pathway.code,
                "stages_count": len(pathway_in.stages),
            },
        )

        return self.get_pathway(db, pathway.pathway_id)

    def get_pathway(self, db: Session, pathway_id: str) -> RegionalPathwayResponse:
        """Retrieve a clinical pathway definition by ID."""
        pathway = db.query(RegionalClinicalPathway).filter(
            RegionalClinicalPathway.pathway_id == pathway_id
        ).first()
        if not pathway:
            raise ValueError(f"Pathway '{pathway_id}' not found.")

        stages_resp = []
        for stg in pathway.stages:
            ms_resp = [
                PathwayMilestoneResponse(
                    milestone_id=ms.milestone_id,
                    stage_id=ms.stage_id,
                    name=ms.name,
                    criteria_code=ms.criteria_code,
                    expected_order_type=ms.expected_order_type,
                    is_critical=ms.is_critical,
                )
                for ms in stg.milestones
            ]
            stages_resp.append(
                PathwayStageResponse(
                    stage_id=stg.stage_id,
                    pathway_id=stg.pathway_id,
                    sequence_order=stg.sequence_order,
                    name=stg.name,
                    description=stg.description,
                    assigned_facility_id=stg.assigned_facility_id,
                    target_duration_minutes=stg.target_duration_minutes,
                    required_role=stg.required_role,
                    clinical_criteria_json=stg.clinical_criteria_json or {},
                    is_mandatory=stg.is_mandatory,
                    milestones=ms_resp,
                )
            )

        return RegionalPathwayResponse(
            pathway_id=pathway.pathway_id,
            code=pathway.code,
            name=pathway.name,
            category=pathway.category,
            description=pathway.description,
            tenant_id=pathway.tenant_id,
            version=pathway.version,
            target_duration_hours=pathway.target_duration_hours,
            is_active=pathway.is_active,
            created_at=pathway.created_at,
            stages=stages_resp,
        )

    def list_pathways(self, db: Session) -> List[RegionalPathwayResponse]:
        """List all defined regional clinical pathways."""
        pathways = db.query(RegionalClinicalPathway).filter(
            RegionalClinicalPathway.is_active == True
        ).all()
        return [self.get_pathway(db, p.pathway_id) for p in pathways]

    def enroll_patient(
        self,
        db: Session,
        patient_id: str,
        pathway_id: str,
        user: User,
        facility_id: Optional[str] = None,
    ) -> PatientPathwayEnrollmentResponse:
        """Enroll patient in a regional clinical pathway starting at Stage 1."""
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient with ID '{patient_id}' not found.")

        pathway = db.query(RegionalClinicalPathway).filter(
            RegionalClinicalPathway.pathway_id == pathway_id,
            RegionalClinicalPathway.is_active == True,
        ).first()
        if not pathway:
            raise ValueError(f"Active clinical pathway '{pathway_id}' not found.")

        if not pathway.stages:
            raise ValueError("Clinical pathway has no configured stages.")

        first_stage = pathway.stages[0]
        enrollment_id = f"ENR-{uuid.uuid4().hex[:10].upper()}"
        active_facility = facility_id or getattr(patient, "facility_id", "FAC-001") or "FAC-001"

        enrollment = PatientPathwayEnrollment(
            enrollment_id=enrollment_id,
            patient_id=patient.patient_id,
            pathway_id=pathway.pathway_id,
            facility_id=active_facility,
            current_stage_id=first_stage.stage_id,
            status="active",
            assigned_care_team_user_id=user.id,
            completed_milestones=[],
            has_variance=False,
        )
        db.add(enrollment)
        db.flush()

        # Record initial stage start event
        event = PatientPathwayStageEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}",
            enrollment_id=enrollment.enrollment_id,
            stage_id=first_stage.stage_id,
            facility_id=active_facility,
            actor_user_id=user.id,
            transition_type="start",
            started_at=datetime.now(timezone.utc),
            variance_detected=False,
        )
        db.add(event)
        db.commit()

        # Outbox event
        outbox = OutboxEvent(
            event_id=f"OUT-{uuid.uuid4().hex[:12].upper()}",
            event_type="REGIONAL_PATHWAY_ENROLLED",
            aggregate_type="PatientPathwayEnrollment",
            aggregate_id=enrollment.enrollment_id,
            facility_id=active_facility,
            payload_json={
                "enrollment_id": enrollment.enrollment_id,
                "patient_id": patient.patient_id,
                "pathway_id": pathway.pathway_id,
                "stage_id": first_stage.stage_id,
            },
        )
        db.add(outbox)
        db.commit()

        audit_service.emit_audit_event(
            db=db,
            user_id=user.id,
            action="REGIONAL_PATHWAY_PATIENT_ENROLLED",
            resource_type="PatientPathwayEnrollment",
            resource_id=enrollment.enrollment_id,
            patient_id=patient.patient_id,
            metadata={
                "patient_id": patient.patient_id,
                "pathway_id": pathway.pathway_id,
                "initial_stage": first_stage.name,
            },
        )

        return self.get_enrollment(db, enrollment.enrollment_id)

    def advance_stage(
        self,
        db: Session,
        enrollment_id: str,
        user: User,
        target_stage_id: Optional[str] = None,
        variance_reason: Optional[str] = None,
    ) -> PatientPathwayEnrollmentResponse:
        """Advance enrollment to the next stage with cross-facility verification and outbox event dispatch."""
        enrollment = db.query(PatientPathwayEnrollment).filter(
            PatientPathwayEnrollment.enrollment_id == enrollment_id,
            PatientPathwayEnrollment.status == "active",
        ).first()
        if not enrollment:
            raise ValueError(f"Active pathway enrollment '{enrollment_id}' not found.")

        pathway = enrollment.pathway
        stages = sorted(pathway.stages, key=lambda s: s.sequence_order)
        current_idx = next((i for i, s in enumerate(stages) if s.stage_id == enrollment.current_stage_id), -1)

        if current_idx == -1:
            raise ValueError("Corrupted stage state in enrollment.")

        current_stage = stages[current_idx]

        # Determine next stage
        if target_stage_id:
            next_stage = next((s for s in stages if s.stage_id == target_stage_id), None)
            if not next_stage:
                raise ValueError(f"Target stage '{target_stage_id}' does not belong to this pathway.")
        else:
            if current_idx + 1 < len(stages):
                next_stage = stages[current_idx + 1]
            else:
                next_stage = None  # Reached pathway completion

        source_facility = current_stage.assigned_facility_id or enrollment.facility_id
        dest_facility = next_stage.assigned_facility_id if next_stage else source_facility

        # Verify cross-facility authorization if transferring between facilities
        if dest_facility and source_facility and dest_facility != source_facility:
            is_authorized = verify_cross_facility_transfer_authorization(
                db=db,
                user=user,
                source_facility_id=source_facility,
                destination_facility_id=dest_facility,
                patient_id=enrollment.patient_id,
            )
            if not is_authorized:
                raise PermissionError(
                    f"User '{user.name}' is unauthorized for cross-facility transfer from '{source_facility}' to '{dest_facility}'."
                )

        now = datetime.now(timezone.utc)

        # Close current stage event
        last_event = db.query(PatientPathwayStageEvent).filter(
            PatientPathwayStageEvent.enrollment_id == enrollment.enrollment_id,
            PatientPathwayStageEvent.stage_id == current_stage.stage_id,
            PatientPathwayStageEvent.completed_at.is_(None),
        ).first()

        if last_event:
            last_event.completed_at = now
            duration = int((now - last_event.started_at.replace(tzinfo=timezone.utc)).total_seconds() / 60)
            last_event.duration_minutes = duration
            if variance_reason:
                last_event.variance_detected = True
                last_event.variance_reason = variance_reason
                enrollment.has_variance = True
                enrollment.variance_notes = variance_reason

        if next_stage:
            enrollment.current_stage_id = next_stage.stage_id
            if next_stage.assigned_facility_id:
                enrollment.facility_id = next_stage.assigned_facility_id

            new_event = PatientPathwayStageEvent(
                event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}",
                enrollment_id=enrollment.enrollment_id,
                stage_id=next_stage.stage_id,
                facility_id=dest_facility or enrollment.facility_id,
                actor_user_id=user.id,
                transition_type="advance",
                started_at=now,
                variance_detected=bool(variance_reason),
                variance_reason=variance_reason,
            )
            db.add(new_event)
        else:
            # Pathway completed
            enrollment.status = "completed"
            enrollment.completed_at = now

        db.commit()

        # Emit transactional outbox event
        outbox = OutboxEvent(
            event_id=f"OUT-{uuid.uuid4().hex[:12].upper()}",
            event_type="REGIONAL_PATHWAY_STAGE_TRANSITION",
            aggregate_type="PatientPathwayEnrollment",
            aggregate_id=enrollment.enrollment_id,
            facility_id=enrollment.facility_id,
            payload_json={
                "enrollment_id": enrollment.enrollment_id,
                "patient_id": enrollment.patient_id,
                "previous_stage_id": current_stage.stage_id,
                "new_stage_id": next_stage.stage_id if next_stage else "COMPLETED",
                "source_facility": source_facility,
                "destination_facility": dest_facility,
                "variance_detected": bool(variance_reason),
            },
        )
        db.add(outbox)
        db.commit()

        audit_service.emit_audit_event(
            db=db,
            user_id=user.id,
            action="REGIONAL_PATHWAY_STAGE_ADVANCED",
            resource_type="PatientPathwayEnrollment",
            resource_id=enrollment.enrollment_id,
            patient_id=enrollment.patient_id,
            metadata={
                "from_stage": current_stage.name,
                "to_stage": next_stage.name if next_stage else "Pathway Completed",
                "source_facility": source_facility,
                "destination_facility": dest_facility,
            },
        )

        return self.get_enrollment(db, enrollment.enrollment_id)

    def complete_milestone(
        self,
        db: Session,
        enrollment_id: str,
        milestone_id: str,
        user: User,
        notes: Optional[str] = None,
    ) -> PatientPathwayEnrollmentResponse:
        """Mark a required clinical milestone as fulfilled."""
        enrollment = db.query(PatientPathwayEnrollment).filter(
            PatientPathwayEnrollment.enrollment_id == enrollment_id,
            PatientPathwayEnrollment.status == "active",
        ).first()
        if not enrollment:
            raise ValueError(f"Active enrollment '{enrollment_id}' not found.")

        completed = list(enrollment.completed_milestones or [])
        if milestone_id not in completed:
            completed.append(milestone_id)
            enrollment.completed_milestones = completed
            db.commit()

        audit_service.emit_audit_event(
            db=db,
            user_id=user.id,
            action="REGIONAL_PATHWAY_MILESTONE_COMPLETED",
            resource_type="PatientPathwayEnrollment",
            resource_id=enrollment.enrollment_id,
            patient_id=enrollment.patient_id,
            metadata={
                "milestone_id": milestone_id,
                "notes": notes,
            },
        )

        return self.get_enrollment(db, enrollment.enrollment_id)

    def get_enrollment(self, db: Session, enrollment_id: str) -> PatientPathwayEnrollmentResponse:
        """Retrieve detailed patient enrollment record with events and pathway structure."""
        enrollment = db.query(PatientPathwayEnrollment).filter(
            PatientPathwayEnrollment.enrollment_id == enrollment_id
        ).first()
        if not enrollment:
            raise ValueError(f"Enrollment '{enrollment_id}' not found.")

        pathway_resp = self.get_pathway(db, enrollment.pathway_id)
        events_resp = [
            PatientPathwayEventResponse(
                event_id=ev.event_id,
                stage_id=ev.stage_id,
                facility_id=ev.facility_id,
                actor_user_id=ev.actor_user_id,
                transition_type=ev.transition_type,
                started_at=ev.started_at,
                completed_at=ev.completed_at,
                duration_minutes=ev.duration_minutes,
                variance_detected=ev.variance_detected,
                variance_reason=ev.variance_reason,
            )
            for ev in enrollment.events
        ]

        return PatientPathwayEnrollmentResponse(
            enrollment_id=enrollment.enrollment_id,
            patient_id=enrollment.patient_id,
            pathway_id=enrollment.pathway_id,
            facility_id=enrollment.facility_id,
            current_stage_id=enrollment.current_stage_id,
            status=enrollment.status,
            enrolled_at=enrollment.enrolled_at,
            completed_at=enrollment.completed_at,
            assigned_care_team_user_id=enrollment.assigned_care_team_user_id,
            completed_milestones=enrollment.completed_milestones or [],
            variance_notes=enrollment.variance_notes,
            has_variance=enrollment.has_variance,
            updated_at=enrollment.updated_at,
            pathway=pathway_resp,
            events=events_resp,
        )

    def get_patient_enrollments(
        self,
        db: Session,
        patient_id: str,
    ) -> List[PatientPathwayEnrollmentResponse]:
        """List all clinical pathway enrollments for a patient."""
        enrollments = db.query(PatientPathwayEnrollment).filter(
            PatientPathwayEnrollment.patient_id == patient_id
        ).order_by(PatientPathwayEnrollment.enrolled_at.desc()).all()

        return [self.get_enrollment(db, e.enrollment_id) for e in enrollments]


pathway_service = PathwayService()
