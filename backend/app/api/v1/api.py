from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    appointments,
    auth,
    bulk_export,
    care_plans,
    cds,
    chat,
    cohorts,
    doctors,
    documents,
    encounters,
    fhir,
    fhir_subscriptions,
    health,
    imaging,
    media,
    mfa,
    notes,
    orders,
    outbox,
    patients,
    quality,
    rag,
    rpm,
    safety,
    security,
    smart,
    tasks,
    tenants,
    terminology,
    timeline,
    transitions,
    trials,
    vitals,
    websockets,
)


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(mfa.router)
api_router.include_router(patients.router)
api_router.include_router(encounters.router)
api_router.include_router(doctors.router)
api_router.include_router(appointments.router)
api_router.include_router(documents.router)
api_router.include_router(media.router)
api_router.include_router(notes.router)
api_router.include_router(vitals.router)
api_router.include_router(care_plans.router)
api_router.include_router(cohorts.router)
api_router.include_router(transitions.router)
api_router.include_router(orders.router)
api_router.include_router(outbox.router)
api_router.include_router(quality.router, prefix="/quality", tags=["Quality Measures & Compliance"])
api_router.include_router(rpm.router, prefix="/rpm", tags=["Remote Patient Monitoring & Telehealth"])
api_router.include_router(trials.router, tags=["Clinical Trials & Precision Oncology"])
api_router.include_router(agents.router, tags=["Clinical AI Agents & Care Coordination"])
api_router.include_router(imaging.router, tags=["Medical Imaging & Radiology"])
api_router.include_router(security.router, tags=["Clinical Security & Compliance Governance"])
api_router.include_router(smart.router, prefix="/smart", tags=["SMART on FHIR 2.0"])
api_router.include_router(cds.router, prefix="/cds-services", tags=["CDS Hooks 2.0"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Multi-Tenant Health Systems"])
api_router.include_router(terminology.router, prefix="/terminology", tags=["Clinical Terminology Normalization"])
api_router.include_router(websockets.router, tags=["WebSockets & WebRTC Signaling"])
api_router.include_router(fhir_subscriptions.router)
api_router.include_router(bulk_export.router)
api_router.include_router(rag.router)

api_router.include_router(chat.router)
api_router.include_router(timeline.router)
api_router.include_router(safety.router)
api_router.include_router(fhir.router)
api_router.include_router(tasks.router)
api_router.include_router(health.router)
