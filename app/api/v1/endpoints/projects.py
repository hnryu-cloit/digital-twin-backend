from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import get_current_user_id
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectSummaryResponse,
    ProjectUpdateRequest,
)
from app.services.db_store import store

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreateRequest, user_id: str = Depends(get_current_user_id)):
    project = store.create_project(body.model_dump(), user_id=user_id)
    return ProjectDetailResponse(**project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    _: str = Depends(get_current_user_id),
):
    items = sorted(store.list_projects(), key=lambda item: item["updated_at"], reverse=True)
    start = (page - 1) * size
    paged_items = items[start : start + size]
    return ProjectListResponse(
        items=[ProjectSummaryResponse(**item) for item in paged_items],
        page=page,
        size=size,
        total=len(items),
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str, _: str = Depends(get_current_user_id)):
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return ProjectDetailResponse(**project)


@router.patch("/{project_id}", response_model=ProjectDetailResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    _: str = Depends(get_current_user_id),
):
    project = store.update_project(project_id, body.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return ProjectDetailResponse(**project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, _: str = Depends(get_current_user_id)):
    if not store.soft_delete_project(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
