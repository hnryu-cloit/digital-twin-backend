from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.settings import (
    LlmParameterRequest,
    LlmParameterResponse,
    PromptSettingsRequest,
    PromptSettingsResponse,
)
from app.services.mock_store import store

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/prompts/{prompt_type}", response_model=PromptSettingsResponse)
async def get_prompt(prompt_type: str, _: str = Depends(get_current_user_id)):
    prompt = store.prompts.get(prompt_type, "")
    return PromptSettingsResponse(prompt_type=prompt_type, prompt=prompt)


@router.put("/prompts", response_model=PromptSettingsResponse)
async def save_prompt(body: PromptSettingsRequest, _: str = Depends(get_current_user_id)):
    store.prompts[body.prompt_type] = body.prompt
    return PromptSettingsResponse(prompt_type=body.prompt_type, prompt=body.prompt)


@router.get("/llm-parameters", response_model=LlmParameterResponse)
async def get_llm_parameters(_: str = Depends(get_current_user_id)):
    return LlmParameterResponse(**store.llm_parameters)


@router.put("/llm-parameters", response_model=LlmParameterResponse)
async def save_llm_parameters(body: LlmParameterRequest, _: str = Depends(get_current_user_id)):
    store.llm_parameters = body.model_dump()
    return LlmParameterResponse(**store.llm_parameters)
