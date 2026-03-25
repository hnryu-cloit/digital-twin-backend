from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AIJobResponse(BaseModel):
    id: str
    project_id: str
    job_type: str
    status: str
    progress: int
    payload: dict = Field(default_factory=dict)
    result_ref: Optional[dict] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_by: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AIJobListResponse(BaseModel):
    items: list[AIJobResponse]
    total: int
