from fastapi import APIRouter

from app.api.v1.endpoints import (
    assistant,
    ai_jobs,
    auth,
    data,
    personas,
    individual_personas,
    projects,
    reports,
    segments,
    settings,
    simulations,
    surveys,
)

router = APIRouter(prefix="/api")
router.include_router(auth.router)
router.include_router(ai_jobs.router)
router.include_router(data.router)
router.include_router(projects.router)
router.include_router(personas.router)
router.include_router(individual_personas.router, prefix="/individual-personas", tags=["individual-personas"])
router.include_router(segments.router)
router.include_router(surveys.router)
router.include_router(simulations.router)
router.include_router(reports.router)
router.include_router(assistant.router)
router.include_router(settings.router)
