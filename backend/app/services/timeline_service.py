"""Longitudinal Clinical Timeline Service.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
Aggregates authoritative clinical records (encounters, appointments, documents,
and extracted clinical facts) into a unified chronological patient timeline.
Provides RAG-grounded longitudinal summary synthesis with verified citations.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.document import DocumentChunk, MedicalDocument
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User
from app.schemas.rag import RAGCitation
from app.schemas.timeline import (
    ClinicalTimelineEvent,
    TimelineEventType,
    TimelineListResponse,
    TimelineSummaryResponse,
)
from app.services.rag_service import execute_rag_query, validate_patient_rag_access

logger = logging.getLogger("medigen.timeline")


def _generate_event_id() -> str:
    """Generate unique timeline event identifier."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_part = uuid.uuid4().hex[:8].upper()
    return f"EVT-{date_part}-{unique_part}"


def _extract_chunk_clinical_events(
    patient_id_str: str,
    doc: MedicalDocument,
    chunk: DocumentChunk,
) -> list[ClinicalTimelineEvent]:
    """Derive granular clinical events from document chunks (diagnoses, medications, lab findings)."""
    events: list[ClinicalTimelineEvent] = []
    content = chunk.content
    doc_date = doc.created_at or datetime.now(timezone.utc)
    if doc_date.tzinfo is None:
        doc_date = doc_date.replace(tzinfo=timezone.utc)

    citation = RAGCitation(
        document_id=doc.document_id,
        title=doc.title,
        page_number=chunk.page_number,
        chunk_id=chunk.chunk_id,
        document_type=doc.document_type,
    )

    # Detect Diagnosis lines
    diag_matches = re.finditer(
        r"(?:diagnosis|diagnoses|impression|assessment)\s*:\s*([^\n\.;]+)",
        content,
        re.IGNORECASE,
    )
    for m in diag_matches:
        diag_text = m.group(1).strip()
        if len(diag_text) >= 3:
            events.append(
                ClinicalTimelineEvent(
                    event_id=_generate_event_id(),
                    patient_id=patient_id_str,
                    event_date=doc_date,
                    event_type=TimelineEventType.DIAGNOSIS,
                    title=f"Diagnosis: {diag_text[:80]}",
                    description=f"Documented clinical diagnosis: {diag_text}",
                    source_document_id=doc.document_id,
                    source_chunk_id=chunk.chunk_id,
                    page_number=chunk.page_number,
                    confidence=0.95,
                    citations=[citation],
                )
            )

    # Detect Prescribed / Discharge Medications
    med_matches = re.finditer(
        r"(?:prescribed|discharge medications?|medications?|rx)\s*:\s*([^\n\.;]+)",
        content,
        re.IGNORECASE,
    )
    for m in med_matches:
        med_text = m.group(1).strip()
        if len(med_text) >= 3:
            events.append(
                ClinicalTimelineEvent(
                    event_id=_generate_event_id(),
                    patient_id=patient_id_str,
                    event_date=doc_date,
                    event_type=TimelineEventType.MEDICATION_PRESCRIBED,
                    title=f"Medication: {med_text[:80]}",
                    description=f"Documented medication order: {med_text}",
                    source_document_id=doc.document_id,
                    source_chunk_id=chunk.chunk_id,
                    page_number=chunk.page_number,
                    confidence=0.95,
                    citations=[citation],
                )
            )

    # Detect Lab / Diagnostic Results
    lab_matches = re.finditer(
        r"(?:lab results?|findings?|investigation|labs?|panel)\s*:\s*([^\n\.;]+)",
        content,
        re.IGNORECASE,
    )
    for m in lab_matches:
        lab_text = m.group(1).strip()
        if len(lab_text) >= 3:
            events.append(
                ClinicalTimelineEvent(
                    event_id=_generate_event_id(),
                    patient_id=patient_id_str,
                    event_date=doc_date,
                    event_type=TimelineEventType.LAB_RESULT,
                    title=f"Lab/Finding: {lab_text[:80]}",
                    description=f"Clinical diagnostic result: {lab_text}",
                    source_document_id=doc.document_id,
                    source_chunk_id=chunk.chunk_id,
                    page_number=chunk.page_number,
                    confidence=0.90,
                    citations=[citation],
                )
            )

    return events


def get_patient_timeline(
    db: Session,
    patient_id_str: str,
    current_user: User,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    event_type: Optional[TimelineEventType] = None,
    skip: int = 0,
    limit: int = 50,
    sort_order: str = "desc",
) -> TimelineListResponse:
    """Build and filter a longitudinal clinical timeline for the authorized patient."""
    from app.services.appointment_service import resolve_patient

    patient = resolve_patient(db, patient_id_str)
    if not patient:
        raise KeyError(f"Patient '{patient_id_str}' not found.")

    validate_patient_rag_access(db, current_user, patient)
    raw_events: list[ClinicalTimelineEvent] = []

    # 1. Authoritative Encounters
    encounters = db.scalars(
        select(Encounter).where(Encounter.patient_id == patient.id)
    ).all()
    for enc in encounters:
        enc_date = enc.encounter_date or enc.created_at
        if enc_date.tzinfo is None:
            enc_date = enc_date.replace(tzinfo=timezone.utc)
        raw_events.append(
            ClinicalTimelineEvent(
                event_id=_generate_event_id(),
                patient_id=patient.patient_id,
                event_date=enc_date,
                event_type=TimelineEventType.ENCOUNTER,
                title=f"Encounter: {enc.encounter_type.value.replace('_', ' ').title()}",
                description=f"Chief Complaint: {enc.chief_complaint}. Assessment: {enc.assessment or 'None'}. Notes: {enc.clinical_notes or 'None'}",
                source_document_id=None,
                source_chunk_id=None,
                page_number=None,
                confidence=1.0,
                citations=[],
            )
        )

    # 2. Authoritative Appointments
    appointments = db.scalars(
        select(Appointment).where(Appointment.patient_id == patient.id)
    ).all()
    for appt in appointments:
        appt_date = appt.appointment_date
        if appt_date.tzinfo is None:
            appt_date = appt_date.replace(tzinfo=timezone.utc)
        raw_events.append(
            ClinicalTimelineEvent(
                event_id=_generate_event_id(),
                patient_id=patient.patient_id,
                event_date=appt_date,
                event_type=TimelineEventType.APPOINTMENT,
                title=f"Appointment: {appt.reason_for_visit} ({appt.status.upper()})",
                description=f"Mode: {appt.consultation_mode}, Duration: {appt.duration_minutes}m. Reason: {appt.reason_for_visit}. Notes: {appt.notes or 'None'}",
                source_document_id=None,
                source_chunk_id=None,
                page_number=None,
                confidence=1.0,
                citations=[],
            )
        )

    # 3. Authoritative Medical Documents & Extracted Clinical Facts
    documents = db.scalars(
        select(MedicalDocument).where(MedicalDocument.patient_id == patient.id)
    ).all()
    for doc in documents:
        doc_date = doc.created_at
        if doc_date.tzinfo is None:
            doc_date = doc_date.replace(tzinfo=timezone.utc)
        doc_citation = RAGCitation(
            document_id=doc.document_id,
            title=doc.title,
            page_number=1,
            chunk_id=doc.document_id,
            document_type=doc.document_type,
        )
        raw_events.append(
            ClinicalTimelineEvent(
                event_id=_generate_event_id(),
                patient_id=patient.patient_id,
                event_date=doc_date,
                event_type=TimelineEventType.DOCUMENT_UPLOAD,
                title=f"Document: {doc.title} ({doc.document_type.replace('_', ' ').title()})",
                description=f"Uploaded file: {doc.original_filename} ({doc.file_size_bytes} bytes). Total Chunks: {doc.total_chunks}.",
                source_document_id=doc.document_id,
                source_chunk_id=None,
                page_number=None,
                confidence=1.0,
                citations=[doc_citation],
            )
        )

        # Process chunks for fine-grained clinical facts
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        ).all()
        for chunk in chunks:
            extracted = _extract_chunk_clinical_events(patient.patient_id, doc, chunk)
            raw_events.extend(extracted)

    # Apply date filters
    filtered_events: list[ClinicalTimelineEvent] = []
    for ev in raw_events:
        ev_dt = ev.event_date
        if start_date:
            s_dt = start_date if start_date.tzinfo else start_date.replace(tzinfo=timezone.utc)
            if ev_dt < s_dt:
                continue
        if end_date:
            e_dt = end_date if end_date.tzinfo else end_date.replace(tzinfo=timezone.utc)
            if ev_dt > e_dt:
                continue
        if event_type and ev.event_type != event_type:
            continue
        filtered_events.append(ev)

    # Sort events
    reverse = sort_order.lower() != "asc"
    filtered_events.sort(key=lambda x: x.event_date, reverse=reverse)

    total_count = len(filtered_events)
    paginated_events = filtered_events[skip : skip + limit]

    logger.info(
        "Generated timeline for patient %s: %d total events, %d returned",
        patient.patient_id,
        total_count,
        len(paginated_events),
    )

    return TimelineListResponse(
        total=total_count,
        patient_id=patient.patient_id,
        events=paginated_events,
    )


def get_patient_timeline_summary(
    db: Session,
    patient_id_str: str,
    current_user: User,
) -> TimelineSummaryResponse:
    """Synthesize a grounded longitudinal clinical summary using patient-scoped RAG."""
    from app.schemas.rag import RAGQueryRequest
    from app.services.appointment_service import resolve_patient

    patient = resolve_patient(db, patient_id_str)
    if not patient:
        raise KeyError(f"Patient '{patient_id_str}' not found.")

    validate_patient_rag_access(db, current_user, patient)
    timeline = get_patient_timeline(db, patient_id_str, current_user, limit=100)

    # If no records exist, return clear insufficient information statement
    if timeline.total == 0:
        return TimelineSummaryResponse(
            patient_id=patient.patient_id,
            summary="No longitudinal clinical records, encounters, appointments, or medical documents are currently available for this patient.",
            citations=[],
            event_count=0,
            generated_at=datetime.now(timezone.utc),
        )

    # Formulate clinical summary query executed via grounded RAG pipeline
    summary_prompt = (
        "Synthesize a concise, chronologically grounded longitudinal medical timeline and summary "
        "covering diagnoses, clinical encounters, appointments, and medication history."
    )
    rag_req = RAGQueryRequest(
        patient_id=patient.patient_id,
        query=summary_prompt,
        top_k=8,
    )
    rag_result = execute_rag_query(
        db=db,
        request=rag_req,
        current_user=current_user,
    )

    return TimelineSummaryResponse(
        patient_id=patient.patient_id,
        summary=rag_result.answer,
        citations=rag_result.citations,
        event_count=timeline.total,
        generated_at=datetime.now(timezone.utc),
    )
