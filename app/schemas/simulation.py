from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SimulationControlRequest(BaseModel):
    project_id: str
    action: str


class SimulationControlResponse(BaseModel):
    job_id: str
    status: str
    progress: int


class SimulationProgressResponse(BaseModel):
    project_id: str
    job_id: Optional[str]
    completed_responses: int
    target_responses: int
    progress: int


class ResponseFeedItem(BaseModel):
    id: str
    persona_name: str
    segment: str
    question_id: str
    question_text: str
    selected_option: str
    rationale: str
    integrity_score: float
    timestamp: datetime
    cot: list[str]


class ResponseDistributionItem(BaseModel):
    label: str
    value: float


class InsightResponse(BaseModel):
    summary: str
    strategies: list[str]
    cached_until: datetime


class KeywordTrendItem(BaseModel):
    keyword: str
    frequency: int
    trend: str


class CotResponse(BaseModel):
    response_id: str
    integrity_score: float
    steps: list[str]
    meta: dict[str, str]
