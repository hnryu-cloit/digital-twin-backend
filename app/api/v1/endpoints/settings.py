from fastapi import APIRouter, Depends

from app.core.defaults import DEFAULT_LLM_PARAMETERS, DEFAULT_PROMPTS
from app.core.dependencies import get_current_user_id
from app.schemas.settings import (
    JsonSettingsRequest,
    JsonSettingsResponse,
    LlmParameterRequest,
    LlmParameterResponse,
    PromptSettingsRequest,
    PromptSettingsResponse,
)
from app.services.db_store import store

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/prompts/{prompt_type}", response_model=PromptSettingsResponse)
async def get_prompt(prompt_type: str, _: str = Depends(get_current_user_id)):
    default_prompt = DEFAULT_PROMPTS.get(prompt_type, "")
    prompt = store.get_setting(f"prompt:{prompt_type}", default_prompt)
    return PromptSettingsResponse(prompt_type=prompt_type, prompt=prompt)


@router.put("/prompts", response_model=PromptSettingsResponse)
async def save_prompt(body: PromptSettingsRequest, _: str = Depends(get_current_user_id)):
    store.set_setting(f"prompt:{body.prompt_type}", body.prompt)
    return PromptSettingsResponse(prompt_type=body.prompt_type, prompt=body.prompt)


@router.get("/llm-parameters", response_model=LlmParameterResponse)
async def get_llm_parameters(_: str = Depends(get_current_user_id)):
    params = store.get_setting("llm_parameters", DEFAULT_LLM_PARAMETERS)
    return LlmParameterResponse(**params)


@router.put("/llm-parameters", response_model=LlmParameterResponse)
async def save_llm_parameters(body: LlmParameterRequest, _: str = Depends(get_current_user_id)):
    store.set_setting("llm_parameters", body.model_dump())
    return LlmParameterResponse(**body.model_dump())


@router.get("/kv/{setting_key}", response_model=JsonSettingsResponse)
async def get_json_setting(setting_key: str, _: str = Depends(get_current_user_id)):
    value = store.get_setting(setting_key, {})
    if not isinstance(value, dict):
        value = {}
    return JsonSettingsResponse(key=setting_key, value=value)


@router.put("/kv", response_model=JsonSettingsResponse)
async def save_json_setting(body: JsonSettingsRequest, _: str = Depends(get_current_user_id)):
    store.set_setting(body.key, body.value)
    return JsonSettingsResponse(key=body.key, value=body.value)
