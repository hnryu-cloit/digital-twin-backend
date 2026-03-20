from typing import Optional

from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: Optional[str] = None


class AssistantChatResponse(BaseModel):
    session_id: str
    answer: str
    evidence: list[dict[str, str]]
    confidence: int
