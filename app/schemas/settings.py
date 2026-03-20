from pydantic import BaseModel, Field


class PromptSettingsRequest(BaseModel):
    prompt_type: str = Field(min_length=1)
    prompt: str = Field(min_length=1)


class PromptSettingsResponse(BaseModel):
    prompt_type: str
    prompt: str


class LlmParameterRequest(BaseModel):
    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(ge=0, le=1)


class LlmParameterResponse(BaseModel):
    temperature: float
    top_p: float
