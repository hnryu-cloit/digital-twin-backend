from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user_id
from app.schemas.persona import (
    PersonaDetailResponse,
    PersonaListResponse,
    PersonaPoolCreateRequest,
    PersonaResponse,
)
from app.services.mock_store import store

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("/pool", response_model=PersonaListResponse, status_code=status.HTTP_201_CREATED)
async def create_persona_pool(body: PersonaPoolCreateRequest, _: str = Depends(get_current_user_id)):
    if body.project_id not in store.projects:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    personas = store.create_persona_pool(body.model_dump())
    return PersonaListResponse(items=[PersonaResponse(**item) for item in personas], page=1, size=len(personas), total=len(personas), view_mode="card")


@router.get("", response_model=PersonaListResponse)
async def list_personas(
    project_id: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=12, ge=1, le=100),
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


@router.get("/{persona_id}", response_model=PersonaDetailResponse)
async def get_persona(persona_id: str, _: str = Depends(get_current_user_id)):
    persona = store.get_persona_detail(persona_id)
    if persona is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found.")
    return PersonaDetailResponse(**persona)
