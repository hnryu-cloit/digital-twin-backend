from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.individual_persona import IndividualPersona
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# 응답 스키마
class IndividualPersonaResponse(BaseModel):
    id: int
    index: int
    name: Optional[str]
    job: Optional[str]
    personality: Optional[str]
    samsung_experience: Optional[str]
    age: int
    gender: str
    
    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[IndividualPersonaResponse]

@router.get("/", response_model=PaginatedResponse)
async def get_individual_personas(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """1,000명의 개별 페르소나 목록을 페이징하여 조회합니다."""
    # 전체 개수 조회
    total_count = await db.scalar(select(func.count(IndividualPersona.id)))
    
    # 목록 조회
    offset = (page - 1) * size
    stmt = select(IndividualPersona).offset(offset).limit(size).order_by(IndividualPersona.index)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return {
        "total": total_count,
        "page": page,
        "size": size,
        "items": items
    }

@router.get("/{index}", response_model=IndividualPersonaResponse)
async def get_individual_persona_detail(
    index: int,
    db: AsyncSession = Depends(get_db)
):
    """특정 인덱스의 상세 페르소나 정보를 조회합니다."""
    stmt = select(IndividualPersona).where(IndividualPersona.index == index)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    return item
