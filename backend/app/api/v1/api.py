from fastapi import APIRouter
from app.api.v1.endpoints import (
    appointments,
    auth,
    chat,
    doctors,
    documents,
    encounters,
    fhir,
    health,
    media,
    notes,
    patients,
    rag,
    safety,
    tasks,
    timeline,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(encounters.router)
api_router.include_router(doctors.router)
api_router.include_router(appointments.router)
api_router.include_router(documents.router)
api_router.include_router(media.router)
api_router.include_router(notes.router)
api_router.include_router(rag.router)
api_router.include_router(chat.router)
api_router.include_router(timeline.router)
api_router.include_router(safety.router)
api_router.include_router(fhir.router)
api_router.include_router(tasks.router)
api_router.include_router(health.router)
