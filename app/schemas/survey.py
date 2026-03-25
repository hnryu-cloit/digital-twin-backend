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


class SurveyDraftEvidenceResponse(BaseModel):
    label: str
    value: str


class SurveyDraftQuestionResponse(SurveyQuestionResponse):
    rationale: str
    evidence: list[SurveyDraftEvidenceResponse] = Field(default_factory=list)


class SurveyGenerateRequest(BaseModel):
    project_id: str
    prompt: str = Field(min_length=1)
    survey_type: str = Field(min_length=1)
    question_count: int = Field(default=5, ge=1, le=20)


class SurveyGenerateJobRequest(BaseModel):
    project_id: str
    user_prompt: str = Field(min_length=1)
    survey_type: str = Field(min_length=1)
    question_count: int = Field(default=5, ge=1, le=20)
    template: dict = Field(default_factory=dict)
    segment_context: dict = Field(default_factory=dict)


class SurveyUpdateWithAiRequest(BaseModel):
    prompt: str = Field(min_length=1)
    target_question_id: Optional[str] = None


class SurveyQuestionListResponse(BaseModel):
    project_id: str
    questions: list[SurveyQuestionResponse]


class SurveyDraftPreviewResponse(BaseModel):
    project_id: str
    status: str
    summary: str
    questions: list[SurveyDraftQuestionResponse]


class SurveyDraftSaveRequest(BaseModel):
    questions: list[SurveyQuestionRequest]


class SurveyConfirmRequest(BaseModel):
    project_id: str


class SurveyAiUpdateResponse(BaseModel):
    project_id: str
    questions: list[SurveyQuestionResponse]
    diff: list[str]
