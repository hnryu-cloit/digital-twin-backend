from typing import Optional

from pydantic import BaseModel, Field


class SurveyQuestionRequest(BaseModel):
    text: str = Field(min_length=1)
    type: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)


class SurveyQuestionResponse(SurveyQuestionRequest):
    id: str
    order: int
    status: str


class SurveyGenerateRequest(BaseModel):
    project_id: str
    prompt: str = Field(min_length=1)
    survey_type: str = Field(min_length=1)
    question_count: int = Field(default=5, ge=1, le=20)


class SurveyUpdateWithAiRequest(BaseModel):
    prompt: str = Field(min_length=1)
    target_question_id: Optional[str] = None


class SurveyQuestionListResponse(BaseModel):
    project_id: str
    questions: list[SurveyQuestionResponse]


class SurveyConfirmRequest(BaseModel):
    project_id: str


class SurveyAiUpdateResponse(BaseModel):
    project_id: str
    questions: list[SurveyQuestionResponse]
    diff: list[str]
