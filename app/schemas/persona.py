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
    segment: str
    keywords: list[str]
    interests: list[str]
    preferred_channel: str
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
