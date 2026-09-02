# ==============================================================================
# MediGen AI - Phase 9.0.26: Enterprise CDS Rules, PGx & Order Sets Test Suite
# ==============================================================================

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.cds_pgx import (
    CPICLevel,
    PGxRiskSeverity,
    OrderSetCategory,
    OrderSetItemType,
    OrderSetExecutionStatus,
    CDSRuleTriggerEvent,
    PGxRuleDefinition,
    ClinicalOrderSet,
    CDSRuleEvaluationAudit,
)
from app.models.trials import BiomarkerObservation, GenomicProfile
from app.models.patient import Patient
from app.models.order import ClinicalOrder
from app.models.outbox import OutboxEvent
from app.services.cds_pgx_service import CDSPGxService
from app.core.security import create_access_token


@pytest.fixture
def auth_doctor_token(db_session: Session) -> str:
    """Creates a demo doctor user and returns valid bearer token."""
    doc = db_session.query(User).filter(User.email == "doctor_cds_pgx@example.com").first()
    if not doc:
        doc = User(
            email="doctor_cds_pgx@example.com",
            name="Dr. Gregory House",
            password_hash="mockhashedpassword123",
            role=UserRole.DOCTOR,
            is_active=True,
            default_facility_id="FAC-METRO-MAIN",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
    return create_access_token(subject=str(doc.id), role=doc.role.value)


@pytest.fixture
def auth_patient_token(db_session: Session) -> str:
    """Creates a demo patient user and returns valid bearer token."""
    pat_user = db_session.query(User).filter(User.email == "patient_cds_pgx@example.com").first()
    if not pat_user:
        pat_user = User(
            email="patient_cds_pgx@example.com",
            name="Eleanor Vance",
            password_hash="mockhashedpassword123",
            role=UserRole.PATIENT,
            is_active=True,
            default_facility_id="FAC-METRO-MAIN",
        )
        db_session.add(pat_user)
        db_session.commit()
        db_session.refresh(pat_user)
    return create_access_token(subject=str(pat_user.id), role=pat_user.role.value)


def test_pgx_rules_seed_and_listing(db_session: Session):
    """Verifies that standard CPIC Level A guidelines are seeded and searchable."""
    client = TestClient(app)
    CDSPGxService.seed_defaults_if_needed(db_session)

    # 1. Retrieve all rules
    rules = CDSPGxService.list_pgx_rules(db_session)
    assert len(rules) >= 7

    # 2. Filter by gene CYP2D6
    cyp2d6_rules = CDSPGxService.list_pgx_rules(db_session, gene_symbol="CYP2D6")
    assert len(cyp2d6_rules) >= 2
    assert any(r.drug_name == "Codeine" for r in cyp2d6_rules)

    # 3. Filter by drug Clopidogrel
    clop_rules = CDSPGxService.list_pgx_rules(db_session, drug_name="Clopidogrel")
    assert len(clop_rules) >= 2
    assert any(r.gene_symbol == "CYP2C19" for r in clop_rules)


def test_order_sets_seed_and_retrieval(db_session: Session):
    """Verifies multidisciplinary clinical order sets are seeded with complete item hierarchies."""
    CDSPGxService.seed_defaults_if_needed(db_session)

    # 1. List order sets
    order_sets = CDSPGxService.list_order_sets(db_session)
    assert len(order_sets) >= 3

    # 2. Retrieve Sepsis Resuscitation Bundle
    sepsis = CDSPGxService.get_order_set_by_id(db_session, "ORDSET-SEPSIS-3H")
    assert sepsis is not None
    assert sepsis.code == "SEPSIS_BUNDLE"
    assert sepsis.category == OrderSetCategory.CRITICAL_CARE
    assert len(sepsis.items) >= 5

    # Check item types (Medication, Lab, Nursing)
    item_types = [it.item_type for it in sepsis.items]
    assert OrderSetItemType.MEDICATION in item_types
    assert OrderSetItemType.LAB in item_types
    assert OrderSetItemType.NURSING in item_types


def test_cds_pgx_evaluation_contraindication_alert(db_session: Session):
    """
    Verifies that proposing Codeine for a CYP2D6 Poor Metabolizer patient
    triggers a critical contraindication alert with CPIC alternative recommendations.
    """
    CDSPGxService.seed_defaults_if_needed(db_session)

    patient_id = "PAT-PGX-TEST-001"
    pat = db_session.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not pat:
        pat = Patient(
            patient_id=patient_id,
            first_name="Eleanor",
            last_name="Vance",
            gender="female",
            date_of_birth=date(1985, 5, 12),
        )
        db_session.add(pat)
        db_session.flush()

    gen_prof = GenomicProfile(
        profile_id="GEN-PGX-001",
        patient_id=pat.id,
        test_name="CPIC Pharmacogenomic Panel",
        overall_interpretation="CYP2D6 Poor Metabolizer",
    )
    db_session.add(gen_prof)
    db_session.flush()

    obs = BiomarkerObservation(
        observation_id="BIO-PGX-001",
        profile_id=gen_prof.id,
        patient_id=pat.id,
        gene_symbol="CYP2D6",
        variant_name="*4/*4 (Poor Metabolizer)",
        clinical_significance="Poor Metabolizer",
    )
    db_session.add(obs)
    db_session.commit()

    # Evaluate CDS for proposed medication: Codeine
    result = CDSPGxService.evaluate_cds_and_pgx(
        db=db_session,
        patient_id=patient_id,
        proposed_drug_name="Codeine 30mg Oral",
    )

    assert result["has_alerts"] is True
    assert len(result["cards"]) >= 1

    card = result["cards"][0]
    assert card["gene_symbol"] == "CYP2D6"
    assert card["indicator"] == "critical"
    assert card["severity"] == "contraindicated"
    assert "Morphine" in card["alternative_drugs"] or "Acetaminophen" in card["alternative_drugs"]
    assert len(card["suggestions"]) >= 1


def test_cds_pgx_evaluation_clopidogrel_cyp2c19(db_session: Session):
    """
    Verifies that proposing Clopidogrel for a CYP2C19 Poor Metabolizer patient
    triggers a contraindication alert suggesting Ticagrelor or Prasugrel.
    """
    CDSPGxService.seed_defaults_if_needed(db_session)

    patient_id = "PAT-PGX-TEST-002"
    pat = db_session.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not pat:
        pat = Patient(
            patient_id=patient_id,
            first_name="John",
            last_name="Doe",
            gender="male",
            date_of_birth=date(1978, 2, 10),
        )
        db_session.add(pat)
        db_session.flush()

    gen_prof = GenomicProfile(
        profile_id="GEN-PGX-002",
        patient_id=pat.id,
        test_name="Cardiovascular Pharmacogenomic Panel",
        overall_interpretation="CYP2C19 Poor Metabolizer",
    )
    db_session.add(gen_prof)
    db_session.flush()

    obs = BiomarkerObservation(
        observation_id="BIO-PGX-002",
        profile_id=gen_prof.id,
        patient_id=pat.id,
        gene_symbol="CYP2C19",
        variant_name="*2/*2 (Poor Metabolizer)",
        clinical_significance="Poor Metabolizer",
    )
    db_session.add(obs)
    db_session.commit()

    result = CDSPGxService.evaluate_cds_and_pgx(
        db=db_session,
        patient_id=patient_id,
        proposed_drug_name="Clopidogrel 75mg daily",
    )

    assert result["has_alerts"] is True
    card = result["cards"][0]
    assert card["gene_symbol"] == "CYP2C19"
    assert "Ticagrelor" in card["alternative_drugs"] or "Prasugrel" in card["alternative_drugs"]


def test_order_set_execution_creates_orders_and_outbox(auth_doctor_token: str, db_session: Session):
    """
    Verifies that executing an order set creates discrete ClinicalOrder entries,
    an OrderSetExecution record, and dispatches a Transactional Outbox event.
    """
    CDSPGxService.seed_defaults_if_needed(db_session)

    doc = db_session.query(User).filter(User.email == "doctor_cds_pgx@example.com").first()
    assert doc is not None

    patient_id = "PAT-ORDSET-001"
    facility_id = "FAC-METRO-MAIN"

    res = CDSPGxService.execute_order_set(
        db=db_session,
        order_set_id="ORDSET-SEPSIS-3H",
        patient_id=patient_id,
        ordering_provider_id=doc.id,
        facility_id=facility_id,
        notes="Sepsis protocol initiated from ED triage.",
    )

    assert res["status"] == OrderSetExecutionStatus.EXECUTED or res["status"] == "executed" or res["status"].value == "executed"
    assert res["executed_items_count"] >= 4
    assert len(res["generated_order_ids"]) >= 4

    # Verify orders in database
    pat = db_session.query(Patient).filter(Patient.patient_id == patient_id).first()
    assert pat is not None
    orders = db_session.query(ClinicalOrder).filter(
        ClinicalOrder.patient_id == pat.id
    ).all()
    assert len(orders) >= 4

    # Check for Vancomycin and Lactate orders
    order_names = [o.order_type for o in orders]
    assert any("Lactate" in name for name in order_names)
    assert any("Vancomycin" in name for name in order_names)

    # Verify Transactional Outbox Event
    outbox_event = db_session.query(OutboxEvent).filter(
        OutboxEvent.event_type == "CLINICAL_ORDER_SET_EXECUTED"
    ).first()
    assert outbox_event is not None
    assert outbox_event.payload_json["patient_id"] == patient_id


def test_cds_override_audit_recording(auth_doctor_token: str, db_session: Session):
    """
    Verifies that clinician overrides are recorded with mandatory rationale and tamper-evident audit trail.
    """
    doc = db_session.query(User).filter(User.email == "doctor_cds_pgx@example.com").first()
    assert doc is not None

    patient_id = "PAT-OVR-001"
    res = CDSPGxService.record_cds_override(
        db=db_session,
        patient_id=patient_id,
        rule_type="pgx_interaction",
        trigger_event=CDSRuleTriggerEvent.ORDER_SELECT,
        severity="critical",
        card_summary="CYP2D6 Poor Metabolizer with Codeine",
        card_detail="Reduced active metabolite exposure.",
        override_reason="Patient previously tolerated formulation without adverse reaction. Strict monitoring in place.",
        clinician_id=doc.id,
        facility_id="FAC-METRO-MAIN",
    )

    assert res["is_overridden"] is True
    assert res["audit_id"].startswith("CDS-OVR-")

    # Verify audit in list
    audits = CDSPGxService.list_evaluation_audits(db_session, patient_id=patient_id)
    assert len(audits) >= 1
    assert audits[0].is_overridden is True
    assert "Strict monitoring" in audits[0].override_reason


def test_cds_pgx_api_endpoints(auth_doctor_token: str, auth_patient_token: str, db_session: Session):
    """
    Verifies REST API endpoints for rules, order sets, real-time evaluation, and RBAC restrictions.
    """
    client = TestClient(app)
    CDSPGxService.seed_defaults_if_needed(db_session)

    headers = {"Authorization": f"Bearer {auth_doctor_token}"}
    pat_headers = {"Authorization": f"Bearer {auth_patient_token}"}

    # 1. GET /api/v1/cds-pgx/rules
    res_rules = client.get("/api/v1/cds-pgx/rules", headers=headers)
    assert res_rules.status_code == 200
    data_rules = res_rules.json()
    assert data_rules["total"] >= 7

    # 2. GET /api/v1/cds-pgx/order-sets
    res_os = client.get("/api/v1/cds-pgx/order-sets", headers=headers)
    assert res_os.status_code == 200
    data_os = res_os.json()
    assert data_os["total"] >= 3

    # 3. GET /api/v1/cds-pgx/order-sets/ORDSET-SEPSIS-3H
    res_single = client.get("/api/v1/cds-pgx/order-sets/ORDSET-SEPSIS-3H", headers=headers)
    assert res_single.status_code == 200
    assert res_single.json()["code"] == "SEPSIS_BUNDLE"

    # 4. POST /api/v1/cds-pgx/evaluate
    eval_payload = {
        "patient_id": "PAT-00101",
        "proposed_drug_name": "Codeine 30mg",
    }
    res_eval = client.get if False else client.post("/api/v1/cds-pgx/evaluate", json=eval_payload, headers=headers)
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert eval_data["patient_id"] == "PAT-00101"

    # 5. POST /api/v1/cds-pgx/order-sets/ORDSET-DKA-INPATIENT/execute
    exec_payload = {
        "patient_id": "PAT-00101",
        "notes": "Emergency DKA protocol execution",
    }
    res_exec = client.post(
        "/api/v1/cds-pgx/order-sets/ORDSET-DKA-INPATIENT/execute",
        json=exec_payload,
        headers=headers,
    )
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "executed"

    # 6. RBAC: Patient role cannot execute order sets
    res_pat_exec = client.post(
        "/api/v1/cds-pgx/order-sets/ORDSET-DKA-INPATIENT/execute",
        json=exec_payload,
        headers=pat_headers,
    )
    assert res_pat_exec.status_code == 403
