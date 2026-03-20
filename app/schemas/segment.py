from typing import Optional

from pydantic import BaseModel


class SegmentFilterRequest(BaseModel):
    age_groups: list[str] = []
    genders: list[str] = []
    occupations: list[str] = []
    product_groups: list[str] = []
    channels: list[str] = []
    regions: list[str] = []
    segments: list[str] = []


class SegmentDistributionItem(BaseModel):
    label: str
    count: int
    ratio: float
    color: Optional[str] = None


class SegmentKpiResponse(BaseModel):
    total_personas: int
    average_purchase_intent: float
    marketing_acceptance: float
    brand_preference: float
    change_rate: float
