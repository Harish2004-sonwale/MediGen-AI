"""Federated Enterprise Master Patient Index (EMPI) & Identity Resolution Service."""

from datetime import date, datetime, timezone
import math
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.empi import (
    EMPIMatchReview,
    EMPIMergeHistory,
    EnterprisePatientIdentity,
    PatientIdentityLink,
)
from app.models.patient import Patient
from app.schemas.empi import (
    EMPIMatchCandidate,
    EMPIMatchCandidatesResponse,
    EMPILinkResponse,
    EMPIMergeResponse,
    EMPIMatchReviewItem,
)
from app.services.audit_service import audit_service


# ==============================================================================
# 1. Similarity Algorithms: Jaro-Winkler, Levenshtein, Soundex
# ==============================================================================

def soundex(name: str) -> str:
    """Compute American Soundex phonetic code for a name string."""
    if not name:
        return "0000"
    clean = re.sub(r"[^A-Z]", "", name.upper())
    if not clean:
        return "0000"

    first_letter = clean[0]
    mapping = {
        "B": "1", "F": "1", "P": "1", "V": "1",
        "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
        "D": "3", "T": "3",
        "L": "4",
        "M": "5", "N": "5",
        "R": "6",
    }
    encoded = [first_letter]
    prev_code = mapping.get(first_letter, "0")

    for char in clean[1:]:
        code = mapping.get(char, "0")
        if code != "0":
            if code != prev_code:
                encoded.append(code)
            prev_code = code
        else:
            prev_code = "0"
        if len(encoded) == 4:
            break

    while len(encoded) < 4:
        encoded.append("0")

    return "".join(encoded[:4])


def levenshtein_similarity(s1: str, s2: str) -> float:
    """Compute normalized Levenshtein similarity score between 0.0 and 1.0."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        matrix[i][0] = i
    for j in range(len2 + 1):
        matrix[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,        # deletion
                matrix[i][j - 1] + 1,        # insertion
                matrix[i - 1][j - 1] + cost  # substitution
            )

    distance = matrix[len1][len2]
    max_len = max(len1, len2)
    return max(0.0, 1.0 - (distance / max_len))


def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """Compute Jaro-Winkler string similarity score between 0.0 and 1.0."""
    if not s1 or not s2:
        return 0.0
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if not s2_matches[j] and s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    # Count transpositions
    transpositions = 0
    k = 0
    for i in range(len1):
        if s1_matches[i]:
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

    transpositions /= 2.0
    jaro = (
        (matches / len1) +
        (matches / len2) +
        ((matches - transpositions) / matches)
    ) / 3.0

    # Common prefix length up to 4
    prefix = 0
    for i in range(min(len1, len2, 4)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + (prefix * prefix_weight * (1.0 - jaro))


# ==============================================================================
# 2. EMPI Matching Engine & Feature Comparison
# ==============================================================================

class EMPIService:
    """Enterprise Master Patient Index engine for identity resolution across regional health networks."""

    AUTO_MATCH_THRESHOLD: float = 0.85
    MANUAL_REVIEW_THRESHOLD: float = 0.65

    # Feature weights (Sum = 1.0)
    WEIGHT_NAME: float = 0.35
    WEIGHT_DOB: float = 0.25
    WEIGHT_PHONE: float = 0.15
    WEIGHT_ADDRESS: float = 0.15
    WEIGHT_GENDER: float = 0.10

    def compute_patient_match_score(
        self,
        p1: Patient,
        p2: Patient,
    ) -> Tuple[float, Dict[str, float], str]:
        """
        Evaluate deterministic and probabilistic features between two Patient entities.
        Returns: (overall_score, feature_breakdown, match_grade)
        """
        if p1.patient_id == p2.patient_id:
            return 1.0, {"exact_patient_id": 1.0}, "exact"

        # 1. Exact Email / Contact Identifier override
        if p1.email and p2.email and p1.email.lower().strip() == p2.email.lower().strip():
            email_exact = True
        else:
            email_exact = False

        # Name Scoring: Jaro-Winkler + Soundex
        first_jw = jaro_winkler_similarity(p1.first_name, p2.first_name)
        last_jw = jaro_winkler_similarity(p1.last_name, p2.last_name)
        last_soundex = 1.0 if soundex(p1.last_name) == soundex(p2.last_name) else 0.0
        name_score = (first_jw * 0.4) + (last_jw * 0.4) + (last_soundex * 0.2)

        # Date of Birth Scoring
        if p1.date_of_birth and p2.date_of_birth:
            if p1.date_of_birth == p2.date_of_birth:
                dob_score = 1.0
            elif (
                p1.date_of_birth.year == p2.date_of_birth.year and
                p1.date_of_birth.month == p2.date_of_birth.day and
                p1.date_of_birth.day == p2.date_of_birth.month
            ):
                dob_score = 0.85  # Month/day transposed
            elif (
                abs(p1.date_of_birth.year - p2.date_of_birth.year) <= 1 and
                p1.date_of_birth.month == p2.date_of_birth.month and
                p1.date_of_birth.day == p2.date_of_birth.day
            ):
                dob_score = 0.80  # Off-by-one year typo
            else:
                dob_score = 0.0
        else:
            dob_score = 0.5  # Neutral when missing

        # Phone Number Scoring
        p1_phone = re.sub(r"\D", "", p1.phone or "")
        p2_phone = re.sub(r"\D", "", p2.phone or "")
        if p1_phone and p2_phone:
            if p1_phone == p2_phone:
                phone_score = 1.0
            elif p1_phone[-7:] == p2_phone[-7:] and len(p1_phone) >= 7:
                phone_score = 0.90
            else:
                phone_score = levenshtein_similarity(p1_phone, p2_phone)
        else:
            phone_score = 0.5

        # Address Scoring
        p1_addr = (p1.address or "").lower().strip()
        p2_addr = (p2.address or "").lower().strip()
        if p1_addr and p2_addr:
            address_score = jaro_winkler_similarity(p1_addr, p2_addr)
        else:
            address_score = 0.5

        # Gender Scoring
        if p1.gender and p2.gender:
            gender_score = 1.0 if str(p1.gender).lower() == str(p2.gender).lower() else 0.0
        else:
            gender_score = 0.5

        # Aggregate weighted score
        overall_score = (
            (name_score * self.WEIGHT_NAME) +
            (dob_score * self.WEIGHT_DOB) +
            (phone_score * self.WEIGHT_PHONE) +
            (address_score * self.WEIGHT_ADDRESS) +
            (gender_score * self.WEIGHT_GENDER)
        )

        # Boost exact matching combinations
        if email_exact and (dob_score >= 0.85 or name_score >= 0.85):
            overall_score = max(overall_score, 0.95)

        overall_score = round(min(1.0, max(0.0, overall_score)), 4)

        if overall_score >= self.AUTO_MATCH_THRESHOLD:
            grade = "exact" if overall_score >= 0.95 else "probable"
        elif overall_score >= self.MANUAL_REVIEW_THRESHOLD:
            grade = "possible"
        else:
            grade = "distinct"

        breakdown = {
            "name_score": round(name_score, 4),
            "dob_score": round(dob_score, 4),
            "phone_score": round(phone_score, 4),
            "address_score": round(address_score, 4),
            "gender_score": round(gender_score, 4),
            "overall_score": overall_score,
        }

        return overall_score, breakdown, grade

    def get_or_create_enterprise_identity(
        self,
        db: Session,
        patient: Patient,
        user_id: Optional[int] = None,
    ) -> EnterprisePatientIdentity:
        """Find active EUID for patient, or allocate a new golden record."""
        link = db.query(PatientIdentityLink).filter(
            PatientIdentityLink.patient_id == patient.patient_id
        ).first()

        if link:
            ident = db.query(EnterprisePatientIdentity).filter(
                EnterprisePatientIdentity.enterprise_id == link.enterprise_id
            ).first()
            if ident and ident.status == "active":
                return ident

        # Allocate new Enterprise Master Identity
        euid = f"EUID-{uuid.uuid4().hex[:12].upper()}"
        tenant_id = getattr(patient, "facility_id", "FAC-001") or "FAC-001"

        identity = EnterprisePatientIdentity(
            enterprise_id=euid,
            tenant_id=tenant_id,
            primary_patient_id=patient.patient_id,
            status="active",
            confidence_score=1.0,
        )
        db.add(identity)
        db.flush()

        identity_link = PatientIdentityLink(
            enterprise_id=euid,
            patient_id=patient.patient_id,
            facility_id=getattr(patient, "facility_id", "FAC-001") or "FAC-001",
            link_type="deterministic_exact",
            match_score=1.0,
            created_by_user_id=user_id,
        )
        db.add(identity_link)
        db.commit()
        db.refresh(identity)
        return identity

    def find_candidate_matches(
        self,
        db: Session,
        patient_id: str,
        threshold: Optional[float] = None,
        facility_id: Optional[str] = None,
    ) -> EMPIMatchCandidatesResponse:
        """Scan regional patients and return ranked candidate matches."""
        target = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not target:
            raise ValueError(f"Patient with ID '{patient_id}' not found.")

        min_threshold = threshold if threshold is not None else self.MANUAL_REVIEW_THRESHOLD
        query = db.query(Patient).filter(Patient.patient_id != patient_id)
        other_patients = query.all()

        candidates: List[EMPIMatchCandidate] = []

        for other in other_patients:
            score, features, grade = self.compute_patient_match_score(target, other)
            if score >= min_threshold:
                # Find enterprise ID if linked
                other_link = db.query(PatientIdentityLink).filter(
                    PatientIdentityLink.patient_id == other.patient_id
                ).first()

                cand = EMPIMatchCandidate(
                    patient_id=other.patient_id,
                    facility_id=getattr(other, "facility_id", "FAC-001") or "FAC-001",
                    first_name=other.first_name,
                    last_name=other.last_name,
                    date_of_birth=other.date_of_birth,
                    gender=str(other.gender.value) if hasattr(other.gender, "value") else str(other.gender),
                    phone=other.phone,
                    email=other.email,
                    address=other.address,
                    match_score=score,
                    match_grade=grade,
                    feature_scores=features,
                    enterprise_id=other_link.enterprise_id if other_link else None,
                )
                candidates.append(cand)

                # If candidate is in manual review range, ensure Review record exists
                if self.MANUAL_REVIEW_THRESHOLD <= score < self.AUTO_MATCH_THRESHOLD:
                    self._create_or_update_review_record(db, target, other, score, features)

        candidates.sort(key=lambda c: c.match_score, reverse=True)

        return EMPIMatchCandidatesResponse(
            query_patient_id=patient_id,
            total_candidates=len(candidates),
            auto_match_threshold=self.AUTO_MATCH_THRESHOLD,
            manual_review_threshold=self.MANUAL_REVIEW_THRESHOLD,
            candidates=candidates,
        )

    def _create_or_update_review_record(
        self,
        db: Session,
        p1: Patient,
        p2: Patient,
        score: float,
        features: Dict[str, Any],
    ) -> None:
        """Ensure a pending manual review item is queued for registrar inspection."""
        sorted_pids = sorted([p1.patient_id, p2.patient_id])
        pid_a, pid_b = sorted_pids[0], sorted_pids[1]

        existing = db.query(EMPIMatchReview).filter(
            EMPIMatchReview.patient_id_a == pid_a,
            EMPIMatchReview.patient_id_b == pid_b,
        ).first()

        if not existing:
            rev_id = f"REV-{uuid.uuid4().hex[:10].upper()}"
            review = EMPIMatchReview(
                review_id=rev_id,
                patient_id_a=pid_a,
                patient_id_b=pid_b,
                facility_id_a=getattr(p1, "facility_id", "FAC-001") or "FAC-001",
                facility_id_b=getattr(p2, "facility_id", "FAC-001") or "FAC-001",
                match_score=score,
                feature_breakdown=features,
                status="pending_review",
            )
            db.add(review)
            db.commit()

    def link_patient_record(
        self,
        db: Session,
        enterprise_id: str,
        patient_id: str,
        user_id: Optional[int] = None,
        link_type: str = "manual_link",
    ) -> EMPILinkResponse:
        """Associate a local patient record with an Enterprise Master identity."""
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found.")

        ident = db.query(EnterprisePatientIdentity).filter(
            EnterprisePatientIdentity.enterprise_id == enterprise_id,
            EnterprisePatientIdentity.status == "active",
        ).first()
        if not ident:
            raise ValueError(f"Active Enterprise Identity '{enterprise_id}' not found.")

        existing_link = db.query(PatientIdentityLink).filter(
            PatientIdentityLink.patient_id == patient_id
        ).first()

        facility_id = getattr(patient, "facility_id", "FAC-001") or "FAC-001"

        if existing_link:
            existing_link.enterprise_id = enterprise_id
            existing_link.link_type = link_type
            existing_link.match_score = 1.0
            db.commit()
            db.refresh(existing_link)
            link_record = existing_link
        else:
            link_record = PatientIdentityLink(
                enterprise_id=enterprise_id,
                patient_id=patient_id,
                facility_id=facility_id,
                link_type=link_type,
                match_score=1.0,
                created_by_user_id=user_id,
            )
            db.add(link_record)
            db.commit()
            db.refresh(link_record)

        # Audit Event
        audit_service.emit_audit_event(
            db=db,
            user_id=user_id or 1,
            action="EMPI_PATIENT_LINKED",
            resource_type="EnterprisePatientIdentity",
            resource_id=enterprise_id,
            patient_id=patient_id,
            metadata={
                "patient_id": patient_id,
                "link_type": link_type,
            },
        )

        return EMPILinkResponse(
            enterprise_id=link_record.enterprise_id,
            patient_id=link_record.patient_id,
            facility_id=link_record.facility_id,
            match_score=link_record.match_score,
            link_type=link_record.link_type,
            created_at=link_record.created_at,
        )

    def unlink_patient_record(
        self,
        db: Session,
        patient_id: str,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Remove patient linkage from an Enterprise identity and isolate record."""
        link = db.query(PatientIdentityLink).filter(
            PatientIdentityLink.patient_id == patient_id
        ).first()
        if not link:
            return False

        enterprise_id = link.enterprise_id
        facility_id = link.facility_id
        db.delete(link)
        db.commit()

        audit_service.emit_audit_event(
            db=db,
            user_id=user_id or 1,
            action="EMPI_PATIENT_UNLINKED",
            resource_type="EnterprisePatientIdentity",
            resource_id=enterprise_id,
            patient_id=patient_id,
            metadata={
                "patient_id": patient_id,
                "reason": reason or "Administrative unlink",
            },
        )
        return True

    def merge_patient_identities(
        self,
        db: Session,
        target_patient_id: str,
        source_patient_id: str,
        user_id: int,
        reason: str = "Duplicate patient resolution",
    ) -> EMPIMergeResponse:
        """Merge a source patient identity into a target surviving master identity."""
        if target_patient_id == source_patient_id:
            raise ValueError("Target and source patient IDs cannot be identical.")

        target = db.query(Patient).filter(Patient.patient_id == target_patient_id).first()
        source = db.query(Patient).filter(Patient.patient_id == source_patient_id).first()

        if not target or not source:
            raise ValueError("Both target and source patient records must exist.")

        # Ensure identities
        target_ident = self.get_or_create_enterprise_identity(db, target, user_id)
        source_ident = self.get_or_create_enterprise_identity(db, source, user_id)

        # Update source identity link to point to target enterprise_id
        source_links = db.query(PatientIdentityLink).filter(
            PatientIdentityLink.enterprise_id == source_ident.enterprise_id
        ).all()

        for sl in source_links:
            sl.enterprise_id = target_ident.enterprise_id
            sl.link_type = "manual_merge"

        source_ident.status = "merged"

        merge_id = f"MRG-{uuid.uuid4().hex[:10].upper()}"
        history = EMPIMergeHistory(
            merge_id=merge_id,
            target_enterprise_id=target_ident.enterprise_id,
            source_enterprise_id=source_ident.enterprise_id,
            target_patient_id=target_patient_id,
            source_patient_id=source_patient_id,
            merged_by_user_id=user_id,
            merge_reason=reason,
        )
        db.add(history)
        db.commit()

        # Audit
        audit_service.emit_audit_event(
            db=db,
            user_id=user_id,
            action="EMPI_PATIENTS_MERGED",
            resource_type="EnterprisePatientIdentity",
            resource_id=target_ident.enterprise_id,
            patient_id=target_patient_id,
            metadata={
                "merge_id": merge_id,
                "source_patient_id": source_patient_id,
                "target_patient_id": target_patient_id,
                "source_enterprise_id": source_ident.enterprise_id,
                "target_enterprise_id": target_ident.enterprise_id,
                "reason": reason,
            },
        )

        return EMPIMergeResponse(
            merge_id=merge_id,
            target_enterprise_id=target_ident.enterprise_id,
            source_enterprise_id=source_ident.enterprise_id,
            target_patient_id=target_patient_id,
            source_patient_id=source_patient_id,
            merged_at=history.created_at,
            message=f"Successfully merged source patient '{source_patient_id}' into target '{target_patient_id}'.",
        )

    def split_patient_identity(
        self,
        db: Session,
        merge_id: str,
        user_id: int,
        reason: Optional[str] = None,
    ) -> bool:
        """Revert a previously performed patient merge operation."""
        merge_record = db.query(EMPIMergeHistory).filter(
            EMPIMergeHistory.merge_id == merge_id,
            EMPIMergeHistory.is_reverted == False,
        ).first()

        if not merge_record:
            raise ValueError(f"Active merge history with ID '{merge_id}' not found.")

        # Re-activate source identity
        source_ident = db.query(EnterprisePatientIdentity).filter(
            EnterprisePatientIdentity.enterprise_id == merge_record.source_enterprise_id
        ).first()
        if source_ident:
            source_ident.status = "active"

        # Re-link source patient to source enterprise identity
        source_link = db.query(PatientIdentityLink).filter(
            PatientIdentityLink.patient_id == merge_record.source_patient_id
        ).first()
        if source_link:
            source_link.enterprise_id = merge_record.source_enterprise_id
            source_link.link_type = "manual_split"

        merge_record.is_reverted = True
        merge_record.reverted_by_user_id = user_id
        merge_record.reverted_at = datetime.now(timezone.utc)
        db.commit()

        audit_service.emit_audit_event(
            db=db,
            user_id=user_id,
            action="EMPI_PATIENT_SPLIT_REVERTED",
            resource_type="EnterprisePatientIdentity",
            resource_id=merge_record.target_enterprise_id,
            patient_id=merge_record.target_patient_id,
            metadata={
                "merge_id": merge_id,
                "source_patient_id": merge_record.source_patient_id,
                "target_patient_id": merge_record.target_patient_id,
                "reason": reason or "Administrative merge reversal",
            },
        )
        return True

    def list_match_reviews(
        self,
        db: Session,
        status: Optional[str] = None,
    ) -> List[EMPIMatchReviewItem]:
        """Retrieve list of queued manual match candidate reviews."""
        query = db.query(EMPIMatchReview)
        if status:
            query = query.filter(EMPIMatchReview.status == status)
        query = query.order_by(EMPIMatchReview.created_at.desc())
        items = query.all()

        return [
            EMPIMatchReviewItem(
                review_id=r.review_id,
                patient_id_a=r.patient_id_a,
                patient_id_b=r.patient_id_b,
                facility_id_a=r.facility_id_a,
                facility_id_b=r.facility_id_b,
                match_score=r.match_score,
                feature_breakdown=r.feature_breakdown or {},
                status=r.status,
                reviewed_by_user_id=r.reviewed_by_user_id,
                review_notes=r.review_notes,
                created_at=r.created_at,
            )
            for r in items
        ]

    def resolve_match_review(
        self,
        db: Session,
        review_id: str,
        action: str,
        user_id: int,
        notes: Optional[str] = None,
    ) -> bool:
        """Resolve a queued manual review item with link, merge, or rejection."""
        review = db.query(EMPIMatchReview).filter(
            EMPIMatchReview.review_id == review_id
        ).first()
        if not review:
            raise ValueError(f"Review record '{review_id}' not found.")

        if action == "approve_merge":
            self.merge_patient_identities(
                db=db,
                target_patient_id=review.patient_id_a,
                source_patient_id=review.patient_id_b,
                user_id=user_id,
                reason=notes or "Approved via manual match review",
            )
            review.status = "approved_merged"
        elif action == "approve_link":
            target = db.query(Patient).filter(Patient.patient_id == review.patient_id_a).first()
            if target:
                ident = self.get_or_create_enterprise_identity(db, target, user_id)
                self.link_patient_record(
                    db=db,
                    enterprise_id=ident.enterprise_id,
                    patient_id=review.patient_id_b,
                    user_id=user_id,
                    link_type="manual_link",
                )
            review.status = "approved_linked"
        elif action == "reject_distinct":
            review.status = "rejected_distinct"
        else:
            raise ValueError(f"Unknown review action '{action}'.")

        review.reviewed_by_user_id = user_id
        review.review_notes = notes
        db.commit()
        return True


empi_service = EMPIService()
