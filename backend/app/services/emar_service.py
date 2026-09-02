"""Business service for Closed-Loop Medication Administration Record (eMAR) & Barcode Medication Administration (BCMA).

Phase 9.0.28: Closed-Loop eMAR & Barcode Verification (BCMA), 5-Rights Safety Engine, Dual-Clinician High-Alert Signoff.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.emar import (
    BCMAVerificationLog,
    BCMAVerificationStatus,
    HighAlertMedicationCategory,
    MARStatus,
    MedicationAdministrationRecord,
    MedicationBarcodeDirectory,
)
from app.models.patient import Patient
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.outbox_service import record_outbox_event


# Standard High-Alert Keywords per ISMP Guidelines
HIGH_ALERT_KEYWORDS = [
    "insulin",
    "heparin",
    "warfarin",
    "enoxaparin",
    "hydromorphone",
    "fentanyl",
    "morphine",
    "methotrexate",
    "cisplatin",
    "potassium chloride",
    "rocuronium",
    "vecuronium",
    "digoxin",
    "vancomycin",
]


class EMARService:
    """Enterprise service managing closed-loop eMAR scheduling, bedside BCMA 5-rights verification, and dual witness signoff."""

    @classmethod
    def schedule_medication_doses(
        cls,
        db: Session,
        patient_id: str,
        medication_name: str,
        medication_code: str,
        prescribed_dose: str,
        prescribed_route: str,
        frequency_code: str = "daily",
        order_id: Optional[int] = None,
        facility_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        total_doses: int = 4,
        is_high_alert: Optional[bool] = None,
        requires_dual_witness: Optional[bool] = None,
    ) -> List[MedicationAdministrationRecord]:
        """
        Generates interval-based scheduled eMAR doses for a prescribed medication order.
        """
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found.")

        fac_id = facility_id or patient.facility_id or "FAC-METRO-MAIN"
        start = start_time or datetime.now(timezone.utc)

        # High-Alert Detection
        name_lower = medication_name.lower()
        high_alert = is_high_alert
        if high_alert is None:
            high_alert = any(k in name_lower for k in HIGH_ALERT_KEYWORDS)

        dual_witness = requires_dual_witness
        if dual_witness is None:
            dual_witness = high_alert

        # Frequency interval calculation
        freq = frequency_code.upper()
        interval_hours = 24
        if freq in ("Q4H", "EVERY_4_HOURS"):
            interval_hours = 4
        elif freq in ("Q6H", "EVERY_6_HOURS"):
            interval_hours = 6
        elif freq in ("Q8H", "TID", "3_TIMES_DAILY"):
            interval_hours = 8
        elif freq in ("Q12H", "BID", "2_TIMES_DAILY"):
            interval_hours = 12
        elif freq in ("DAILY", "ONCE_DAILY", "QD"):
            interval_hours = 24
        elif freq in ("STAT", "ONCE", "NOW"):
            total_doses = 1
            interval_hours = 0

        created_records: List[MedicationAdministrationRecord] = []

        for i in range(total_doses):
            scheduled = start + timedelta(hours=i * interval_hours)
            mar_id = f"MAR-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"

            record = MedicationAdministrationRecord(
                mar_id=mar_id,
                order_id=order_id,
                patient_id=patient.id,
                facility_id=fac_id,
                medication_name=medication_name,
                medication_code=medication_code,
                prescribed_dose=prescribed_dose,
                prescribed_route=prescribed_route,
                prescribed_frequency=frequency_code,
                scheduled_time=scheduled,
                status=MARStatus.SCHEDULED,
                is_high_alert=high_alert,
                requires_dual_witness=dual_witness,
            )
            db.add(record)
            created_records.append(record)

        db.commit()
        for r in created_records:
            db.refresh(r)

        return created_records

    @classmethod
    def list_patient_mar_schedule(
        cls,
        db: Session,
        patient_id: str,
        status: Optional[MARStatus] = None,
        limit: int = 50,
    ) -> List[MedicationAdministrationRecord]:
        """Lists patient's eMAR schedule ordered chronologically by scheduled administration time."""
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found.")

        query = db.query(MedicationAdministrationRecord).filter(
            MedicationAdministrationRecord.patient_id == patient.id
        )
        if status:
            query = query.filter(MedicationAdministrationRecord.status == status)

        return query.order_by(MedicationAdministrationRecord.scheduled_time.asc()).limit(limit).all()

    @classmethod
    def verify_5_rights(
        cls,
        db: Session,
        patient_id: str,
        scanned_patient_barcode: str,
        scanned_med_barcode: str,
        mar_id: Optional[str] = None,
        intended_dose: Optional[str] = None,
        intended_route: Optional[str] = None,
        user_id: int = 1,
    ) -> Dict[str, Any]:
        """
        Executes Bedside Barcode Medication Administration (BCMA) 5-Rights Verification:
        1. Right Patient
        2. Right Medication
        3. Right Dose
        4. Right Route
        5. Right Time
        """
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found.")

        # 1. Right Patient Verification
        patient_matched = (
            scanned_patient_barcode.strip().upper() == patient.patient_id.upper()
            or f"PAT-{patient.id}" in scanned_patient_barcode.upper()
            or str(patient.id) == scanned_patient_barcode.strip()
        )

        # 2. Right Medication Lookup
        barcode_entry = (
            db.query(MedicationBarcodeDirectory)
            .filter(MedicationBarcodeDirectory.barcode == scanned_med_barcode.strip())
            .first()
        )

        # Look up MAR record
        mar_record = None
        if mar_id:
            mar_record = (
                db.query(MedicationAdministrationRecord)
                .filter(MedicationAdministrationRecord.mar_id == mar_id)
                .first()
            )
        elif barcode_entry:
            # Match against active scheduled dose
            mar_record = (
                db.query(MedicationAdministrationRecord)
                .filter(
                    MedicationAdministrationRecord.patient_id == patient.id,
                    MedicationAdministrationRecord.status == MARStatus.SCHEDULED,
                    or_(
                        MedicationAdministrationRecord.medication_code == barcode_entry.rxnorm_code,
                        MedicationAdministrationRecord.medication_name.ilike(f"%{barcode_entry.medication_name}%"),
                    ),
                )
                .order_by(MedicationAdministrationRecord.scheduled_time.asc())
                .first()
            )

        medication_matched = False
        dose_matched = False
        route_matched = False
        time_matched = False
        discrepancies: List[str] = []

        now = datetime.now(timezone.utc)

        if not patient_matched:
            discrepancies.append(
                f"Patient Mismatch: Scanned wristband '{scanned_patient_barcode}' does not match patient '{patient.patient_id}'."
            )

        if not barcode_entry and not mar_record:
            discrepancies.append(
                f"Medication Unrecognized: Scanned barcode '{scanned_med_barcode}' is not cataloged in pharmacy directory."
            )

        if mar_record:
            # Medication check
            if barcode_entry:
                medication_matched = (
                    barcode_entry.rxnorm_code == mar_record.medication_code
                    or barcode_entry.medication_name.lower() in mar_record.medication_name.lower()
                    or mar_record.medication_name.lower() in barcode_entry.medication_name.lower()
                )
            else:
                medication_matched = scanned_med_barcode.upper() in mar_record.medication_code.upper()

            if not medication_matched:
                discrepancies.append(
                    f"Medication Mismatch: Scanned drug does not match prescribed '{mar_record.medication_name}'."
                )

            # Dose check
            dose_to_check = intended_dose or (barcode_entry.standard_dose if barcode_entry else None)
            if dose_to_check:
                dose_matched = (
                    dose_to_check.strip().lower() == mar_record.prescribed_dose.strip().lower()
                    or dose_to_check.strip() in mar_record.prescribed_dose
                )
            else:
                dose_matched = True

            if not dose_matched:
                discrepancies.append(
                    f"Dose Variance: Intended dose '{dose_to_check}' differs from prescribed '{mar_record.prescribed_dose}'."
                )

            # Route check
            route_to_check = intended_route or (barcode_entry.route if barcode_entry else None)
            if route_to_check:
                route_matched = route_to_check.strip().lower() == mar_record.prescribed_route.strip().lower()
            else:
                route_matched = True

            if not route_matched:
                discrepancies.append(
                    f"Route Variance: Administration route '{route_to_check}' does not match prescribed '{mar_record.prescribed_route}'."
                )

            # Time check (standard ±60 min window)
            sched = mar_record.scheduled_time
            if sched.tzinfo is None:
                sched = sched.replace(tzinfo=timezone.utc)
            delta_mins = abs((now - sched).total_seconds()) / 60.0
            time_matched = delta_mins <= 60.0

            if not time_matched:
                direction = "Late" if now > sched else "Early"
                discrepancies.append(
                    f"Time Window Variance: Dose is {int(delta_mins)} mins {direction} (Scheduled: {sched.strftime('%H:%M UTC')})."
                )
        else:
            medication_matched = barcode_entry is not None
            dose_matched = True
            route_matched = True
            time_matched = True

        overall_passed = patient_matched and medication_matched and dose_matched and route_matched

        status = BCMAVerificationStatus.PASS
        if not patient_matched or not medication_matched:
            status = BCMAVerificationStatus.MISMATCH_REJECTED
        elif not dose_matched or not route_matched or not time_matched:
            status = BCMAVerificationStatus.WARNING_OVERRIDE

        # Record BCMA verification audit log
        verif_id = f"BCMA-LOG-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"
        log_entry = BCMAVerificationLog(
            verification_id=verif_id,
            mar_id=mar_record.id if mar_record else None,
            patient_id=patient.id,
            user_id=user_id,
            scanned_patient_barcode=scanned_patient_barcode,
            scanned_med_barcode=scanned_med_barcode,
            patient_matched=patient_matched,
            medication_matched=medication_matched,
            dose_matched=dose_matched,
            route_matched=route_matched,
            time_matched=time_matched,
            verification_status=status,
            mismatch_details_json={"discrepancies": discrepancies},
        )
        db.add(log_entry)
        db.commit()

        is_high_alert = bool(mar_record and mar_record.is_high_alert) or (
            bool(barcode_entry and barcode_entry.is_high_alert)
        )
        requires_dual = bool(mar_record and mar_record.requires_dual_witness)

        return {
            "verification_status": status,
            "overall_passed": overall_passed,
            "patient_verification": {
                "passed": patient_matched,
                "expected": patient.patient_id,
                "scanned": scanned_patient_barcode,
            },
            "medication_verification": {
                "passed": medication_matched,
                "expected": mar_record.medication_name if mar_record else (barcode_entry.medication_name if barcode_entry else "N/A"),
                "scanned": barcode_entry.medication_name if barcode_entry else scanned_med_barcode,
            },
            "dose_verification": {
                "passed": dose_matched,
                "expected": mar_record.prescribed_dose if mar_record else "N/A",
                "scanned": intended_dose or (barcode_entry.standard_dose if barcode_entry else "N/A"),
            },
            "route_verification": {
                "passed": route_matched,
                "expected": mar_record.prescribed_route if mar_record else "N/A",
                "scanned": intended_route or (barcode_entry.route if barcode_entry else "N/A"),
            },
            "time_verification": {
                "passed": time_matched,
                "expected": mar_record.scheduled_time.isoformat() if mar_record else "N/A",
                "scanned": now.isoformat(),
            },
            "is_high_alert": is_high_alert,
            "requires_dual_signoff": requires_dual,
            "matched_mar_record": mar_record,
            "discrepancy_warnings": discrepancies,
            "verification_token": verif_id,
            "timestamp": now,
        }

    @classmethod
    def dual_clinician_witness_signoff(
        cls,
        db: Session,
        mar_id: str,
        witness_user_email: str,
        witness_password: str,
        administering_nurse_id: int,
        witness_notes: Optional[str] = None,
    ) -> MedicationAdministrationRecord:
        """
        Authenticates second independent clinician credentials for High-Alert medication dual signoff.
        """
        mar = db.query(MedicationAdministrationRecord).filter(
            MedicationAdministrationRecord.mar_id == mar_id
        ).first()
        if not mar:
            raise ValueError(f"eMAR record ID '{mar_id}' not found.")

        witness_user = db.query(User).filter(User.email == witness_user_email).first()
        if not witness_user:
            raise ValueError("Witness user credentials invalid.")

        if witness_user.id == administering_nurse_id:
            raise ValueError("Dual signoff violation: Witness must be an independent clinician different from the administering nurse.")

        if not verify_password(witness_password, witness_user.password_hash):
            raise ValueError("Witness password verification failed.")

        mar.dual_witness_user_id = witness_user.id
        mar.dual_witness_timestamp = datetime.now(timezone.utc)
        if witness_notes:
            mar.patient_response_notes = (
                f"{mar.patient_response_notes or ''} [Witness Dual-Signoff ({witness_user.name}): {witness_notes}]".strip()
            )

        AuditService().emit_audit_event(
            db=db,
            action="DUAL_WITNESS_SIGNOFF",
            user_id=witness_user.id,
            patient_id=str(mar.patient_id),
            resource_type="MedicationAdministrationRecord",
            resource_id=mar.mar_id,
            metadata={
                "medication_name": mar.medication_name,
                "administering_nurse_id": administering_nurse_id,
                "witness_user_id": witness_user.id,
            },
        )

        db.commit()
        db.refresh(mar)
        return mar

    @classmethod
    def administer_medication(
        cls,
        db: Session,
        mar_id: str,
        administering_nurse_id: int,
        administered_dose: Optional[str] = None,
        administered_route: Optional[str] = None,
        site_of_administration: Optional[str] = None,
        scanned_patient_barcode: Optional[str] = None,
        scanned_med_barcode: Optional[str] = None,
        vital_signs_pre_admin: Optional[dict[str, Any]] = None,
        variance_reason: Optional[str] = None,
        patient_response_notes: Optional[str] = None,
    ) -> MedicationAdministrationRecord:
        """
        Executes formal medication administration signoff on eMAR.
        """
        mar = db.query(MedicationAdministrationRecord).filter(
            MedicationAdministrationRecord.mar_id == mar_id
        ).first()
        if not mar:
            raise ValueError(f"eMAR record ID '{mar_id}' not found.")

        if mar.requires_dual_witness and not mar.dual_witness_user_id:
            raise ValueError(
                "Safety Constraint: High-Alert medication requires independent dual clinician witness signoff before administration."
            )

        mar.status = MARStatus.GIVEN
        mar.actual_admin_time = datetime.now(timezone.utc)
        mar.administering_nurse_id = administering_nurse_id
        mar.administered_dose = administered_dose or mar.prescribed_dose
        mar.administered_route = administered_route or mar.prescribed_route
        mar.site_of_administration = site_of_administration
        mar.barcode_scanned_patient_id = scanned_patient_barcode
        mar.barcode_scanned_med_id = scanned_med_barcode
        mar.vital_signs_pre_admin_json = vital_signs_pre_admin
        mar.variance_reason = variance_reason
        mar.patient_response_notes = patient_response_notes
        mar.verification_passed = True

        AuditService().emit_audit_event(
            db=db,
            action="ADMINISTER_MEDICATION",
            user_id=administering_nurse_id,
            patient_id=str(mar.patient_id),
            resource_type="MedicationAdministrationRecord",
            resource_id=mar.mar_id,
            metadata={
                "medication_name": mar.medication_name,
                "administered_dose": mar.administered_dose,
                "site": site_of_administration,
                "is_high_alert": mar.is_high_alert,
            },
        )

        record_outbox_event(
            db=db,
            event_type="MEDICATION_ADMINISTERED",
            aggregate_type="EMAR",
            aggregate_id=mar.mar_id,
            payload={
                "mar_id": mar.mar_id,
                "patient_id": mar.patient_id,
                "medication_name": mar.medication_name,
                "administered_dose": mar.administered_dose,
                "administered_at": mar.actual_admin_time.isoformat(),
                "nurse_id": administering_nurse_id,
            },
        )

        db.commit()
        db.refresh(mar)
        return mar

    @classmethod
    def hold_or_refuse_medication(
        cls,
        db: Session,
        mar_id: str,
        nurse_id: int,
        status: MARStatus,
        clinical_reason: str,
        patient_response_notes: Optional[str] = None,
    ) -> MedicationAdministrationRecord:
        """Records a held, refused, or omitted medication dose with clinical justification."""
        mar = db.query(MedicationAdministrationRecord).filter(
            MedicationAdministrationRecord.mar_id == mar_id
        ).first()
        if not mar:
            raise ValueError(f"eMAR record ID '{mar_id}' not found.")

        mar.status = status
        mar.actual_admin_time = datetime.now(timezone.utc)
        mar.administering_nurse_id = nurse_id
        mar.variance_reason = clinical_reason
        mar.patient_response_notes = patient_response_notes

        AuditService().emit_audit_event(
            db=db,
            action=f"MEDICATION_{status.value.upper()}",
            user_id=nurse_id,
            patient_id=str(mar.patient_id),
            resource_type="MedicationAdministrationRecord",
            resource_id=mar.mar_id,
            metadata={
                "medication_name": mar.medication_name,
                "reason": clinical_reason,
            },
        )

        db.commit()
        db.refresh(mar)
        return mar

    @classmethod
    def seed_default_barcode_directory_if_needed(cls, db: Session) -> None:
        """Seeds standard hospital medication barcode catalog."""
        count = db.query(MedicationBarcodeDirectory).count()
        if count == 0:
            entries = [
                MedicationBarcodeDirectory(
                    barcode="NDC-00069-0266-01",
                    medication_name="Amlodipine Besylate 5mg",
                    rxnorm_code="RXNORM-17767",
                    ndc_code="00069-0266-01",
                    standard_dose="5mg",
                    dosage_form="tablet",
                    route="oral",
                    is_high_alert=False,
                ),
                MedicationBarcodeDirectory(
                    barcode="NDC-00002-8215-01",
                    medication_name="Insulin Regular (Humulin R) 100 units/mL",
                    rxnorm_code="RXNORM-5856",
                    ndc_code="00002-8215-01",
                    standard_dose="10 units",
                    dosage_form="injection",
                    route="subcutaneous",
                    is_high_alert=True,
                    high_alert_category=HighAlertMedicationCategory.INSULIN,
                ),
                MedicationBarcodeDirectory(
                    barcode="NDC-00641-0400-25",
                    medication_name="Heparin Sodium 5,000 units/mL",
                    rxnorm_code="RXNORM-5224",
                    ndc_code="00641-0400-25",
                    standard_dose="5,000 units",
                    dosage_form="injection",
                    route="subcutaneous",
                    is_high_alert=True,
                    high_alert_category=HighAlertMedicationCategory.ANTICOAGULANT,
                ),
                MedicationBarcodeDirectory(
                    barcode="NDC-00054-0235-25",
                    medication_name="Morphine Sulfate 15mg Oral Tablet",
                    rxnorm_code="RXNORM-7052",
                    ndc_code="00054-0235-25",
                    standard_dose="15mg",
                    dosage_form="tablet",
                    route="oral",
                    is_high_alert=True,
                    high_alert_category=HighAlertMedicationCategory.OPIOID_NARCOTIC,
                ),
                MedicationBarcodeDirectory(
                    barcode="NDC-00093-0147-01",
                    medication_name="Vancomycin IV 1g",
                    rxnorm_code="RXNORM-11124",
                    ndc_code="00093-0147-01",
                    standard_dose="1g",
                    dosage_form="infusion",
                    route="intravenous",
                    is_high_alert=True,
                    high_alert_category=HighAlertMedicationCategory.GENERAL,
                ),
                MedicationBarcodeDirectory(
                    barcode="NDC-00093-7181-56",
                    medication_name="Metoprolol Tartrate 25mg",
                    rxnorm_code="RXNORM-6918",
                    ndc_code="00093-7181-56",
                    standard_dose="25mg",
                    dosage_form="tablet",
                    route="oral",
                    is_high_alert=False,
                ),
            ]
            db.add_all(entries)
            db.commit()
