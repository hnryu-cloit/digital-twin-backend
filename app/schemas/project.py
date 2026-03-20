from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    data_sources: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    target_responses: int = Field(default=1000, ge=1)


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    tags: Optional[list[str]] = None


class ProjectSummaryResponse(BaseModel):
    id: str
    name: str
    type: str
    purpose: str
    status: str
    progress: int
    response_count: int
    target_responses: int
    tags: list[str]
    updated_at: datetime


class ProjectDetailResponse(ProjectSummaryResponse):
    description: Optional[str] = None
    data_sources: list[str]
    surveys_count: int
    reports_count: int
    persona_count: int
    created_by: str
    created_at: datetime
    deleted_at: Optional[datetime] = None


class ProjectListResponse(BaseModel):
    items: list[ProjectSummaryResponse]
    page: int
    size: int
    total: int
