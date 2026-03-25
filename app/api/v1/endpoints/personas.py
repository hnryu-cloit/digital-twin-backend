from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user_id
from app.schemas.ai_job import AIJobResponse
from app.schemas.persona import (
    PersonaDetailResponse,
    PersonaGenerateJobRequest,
    PersonaListResponse,
    PersonaPoolCreateRequest,
    PersonaResponse,
)
from app.services.ai_pipeline_service import import_excel_as_personas, run_persona_generation_pipeline
from app.services.db_store import store

router = APIRouter(prefix="/personas", tags=["personas"])


def _run_generate_persona_job(job_id: str) -> None:
    job = store.get_ai_job(job_id)
    if job is None or job["status"] == "cancelled":
        return

    store.update_ai_job(
        job_id,
        status="running",
        progress=10,
        started_at=datetime.now(timezone.utc),
    )
    try:
        payload = {**(job.get("payload", {}) or {}), "job_id": job_id}
        result_ref = run_persona_generation_pipeline(job["project_id"], payload)
        latest_job = store.get_ai_job(job_id)
        if latest_job and latest_job["status"] == "cancelled":
            return
        store.update_ai_job(
            job_id,
            status="completed",
            progress=100,
            result_ref=result_ref,
            completed_at=datetime.now(timezone.utc),
        )
    except Exception as error:
        store.update_ai_job(
            job_id,
            status="failed",
            progress=100,
            error_code="PERSONA_GENERATION_FAILED",
            error_message=str(error),
            completed_at=datetime.now(timezone.utc),
        )


@router.post("/generate-job", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_personas_job(
    body: PersonaGenerateJobRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    if not store.get_project(body.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    job = store.create_ai_job(
        project_id=body.project_id,
        job_type="persona_generate",
        payload=body.model_dump(),
        created_by=user_id,
    )
    background_tasks.add_task(_run_generate_persona_job, job["id"])
    return AIJobResponse(**job)


@router.post("/pool", response_model=PersonaListResponse, status_code=status.HTTP_201_CREATED)
async def create_persona_pool(body: PersonaPoolCreateRequest, _: str = Depends(get_current_user_id)):
    if not store.get_project(body.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    personas = store.create_persona_pool(body.model_dump())
    return PersonaListResponse(items=[PersonaResponse(**item) for item in personas], page=1, size=len(personas), total=len(personas), view_mode="card")


@router.get("", response_model=PersonaListResponse)
async def list_personas(
    project_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=2000),
    view_mode: str = Query(default="card"),
    search: Optional[str] = None,
    segments: list[str] = Query(default=[]),
    _: str = Depends(get_current_user_id),
):
    personas = store.list_personas(project_id)
    if search:
        lowered = search.lower()
        personas = [item for item in personas if lowered in item["name"].lower() or any(lowered in keyword.lower() for keyword in item["keywords"])]
    if segments:
        personas = [item for item in personas if item["segment"] in segments]
    start = (page - 1) * size
    paged_items = personas[start : start + size]
    return PersonaListResponse(
        items=[PersonaResponse(**item) for item in paged_items],
        page=page,
        size=size,
        total=len(personas),
        view_mode=view_mode,
    )


@router.post("/import-excel", status_code=status.HTTP_200_OK)
async def import_personas_from_excel(
    project_id: str,
    overwrite: bool = True,
    _: str = Depends(get_current_user_id),
):
    try:
        result = import_excel_as_personas(project_id, overwrite=overwrite)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{persona_id}", response_model=PersonaDetailResponse)
async def get_persona(persona_id: str, _: str = Depends(get_current_user_id)):
    persona = store.get_persona_detail(persona_id)
    if persona is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found.")
    return PersonaDetailResponse(**persona)
