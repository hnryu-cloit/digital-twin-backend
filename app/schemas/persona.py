from typing import Optional

from pydantic import BaseModel, Field


class PersonaScoreResponse(BaseModel):
    churn_risk: float
    engagement_score: float
    future_value: float
    data_confidence: float


class PersonaResponse(BaseModel):
    id: str
    project_id: str
    name: str
    age: int
    gender: str
    occupation: str
    occupation_category: str
    region: str
    household_type: str
    segment: str
    keywords: list[str]
    interests: list[str]
    preferred_channel: str
    buy_channel: str
    product_group: str
    purchase_intent: float
    marketing_acceptance: float
    brand_attitude: float
    score: PersonaScoreResponse


class PersonaDetailResponse(PersonaResponse):
    profile: str
    purchase_history: list[str]
    activity_logs: list[str]
    cot: list[str]


class PersonaListResponse(BaseModel):
    items: list[PersonaResponse]
    page: int
    size: int
    total: int
    view_mode: str


class PersonaPoolCreateRequest(BaseModel):
    project_id: str
    segment: str
    age_range: str
    gender: str
    occupation: str
    size: int = Field(default=12, ge=1, le=100)


class PersonaGenerateJobRequest(BaseModel):
    project_id: str
    random_state: int = Field(default=42, ge=0)
    n_synthetic_customers: int = Field(default=1000, ge=100, le=100000)
    n_personas: int = Field(default=7, ge=2, le=20)
    excel_path: Optional[str] = None
    output_dir: Optional[str] = None
    overwrite_existing: bool = True
