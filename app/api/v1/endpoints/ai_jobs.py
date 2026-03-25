from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user_id
from app.schemas.ai_job import AIJobListResponse, AIJobResponse
from app.services.db_store import store

router = APIRouter(prefix="/ai/jobs", tags=["ai-jobs"])


@router.get("", response_model=AIJobListResponse)
async def list_ai_jobs(
    project_id: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
    _: str = Depends(get_current_user_id),
):
    items = store.list_ai_jobs(project_id=project_id, job_type=job_type)
    return AIJobListResponse(items=[AIJobResponse(**item) for item in items], total=len(items))


@router.get("/{job_id}", response_model=AIJobResponse)
async def get_ai_job(job_id: str, _: str = Depends(get_current_user_id)):
    job = store.get_ai_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found.")
    return AIJobResponse(**job)


@router.post("/{job_id}/cancel", response_model=AIJobResponse)
async def cancel_ai_job(job_id: str, _: str = Depends(get_current_user_id)):
    job = store.get_ai_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found.")
    if job["status"] in {"completed", "failed", "cancelled"}:
        return AIJobResponse(**job)
    updated = store.update_ai_job(job_id, status="cancelled", progress=0)
    return AIJobResponse(**updated)
