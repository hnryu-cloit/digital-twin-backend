from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None


class HealthStatusResponse(BaseModel):
    status: str
    database: str
    llm: str
