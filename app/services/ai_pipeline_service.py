from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.services.db_store import store


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_ai_path(path_value: str, *, base_dir: Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def run_persona_generation_pipeline(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    ai_project_dir = _resolve_ai_path(settings.AI_PIPELINE_PROJECT_DIR, base_dir=_repo_root())

    output_dir_value = payload.get("output_dir") or settings.AI_PIPELINE_OUTPUT_DIR
    excel_path_value = payload.get("excel_path") or settings.AI_PIPELINE_EXCEL_PATH
    output_dir = _resolve_ai_path(output_dir_value, base_dir=ai_project_dir)
    excel_path = _resolve_ai_path(excel_path_value, base_dir=ai_project_dir)

    request_payload = {
        "job_id": payload.get("job_id"),
        "project_id": project_id,
        "random_state": payload.get("random_state", 42),
        "n_synthetic_customers": payload.get("n_synthetic_customers", 1000),
        "n_personas": payload.get("n_personas", 7),
        "excel_path": str(excel_path),
        "output_dir": str(output_dir),
        "gemini_api_key": settings.GEMINI_API_KEY,
        "gemini_model_name": payload.get("gemini_model_name", "gemini-3-flash"),
    }
    endpoint = f"{settings.AI_SERVICE_BASE_URL.rstrip('/')}/internal/personas/generate"
    try:
        with httpx.Client(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = client.post(endpoint, json=request_payload)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise RuntimeError(f"AI service request failed: {error}") from error

    result = response.json()
    personas = result.get("personas", [])
    normalized_personas = store.replace_personas(
        project_id,
        personas,
        overwrite_existing=payload.get("overwrite_existing", True),
    )
    return {
        "resource": "personas",
        "project_id": project_id,
        "persona_count": len(normalized_personas),
        "artifacts": result.get("artifacts", {}),
        "metadata": {
            "random_state": request_payload["random_state"],
            "n_synthetic_customers": request_payload["n_synthetic_customers"],
            "n_personas_requested": request_payload["n_personas"],
            "n_personas_generated": len(normalized_personas),
            "ai_service": settings.AI_SERVICE_BASE_URL,
            "pipeline": result.get("metadata", {}),
        },
    }
