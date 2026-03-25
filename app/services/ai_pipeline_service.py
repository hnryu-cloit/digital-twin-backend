from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

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
    ai_src_dir = ai_project_dir / "src"
    if not ai_src_dir.exists():
        raise FileNotFoundError(f"AI source directory not found: {ai_src_dir}")

    if str(ai_src_dir) not in sys.path:
        sys.path.insert(0, str(ai_src_dir))

    from digital_twin_ai.pipeline import run_pipeline

    output_dir_value = payload.get("output_dir") or settings.AI_PIPELINE_OUTPUT_DIR
    excel_path_value = payload.get("excel_path") or settings.AI_PIPELINE_EXCEL_PATH
    output_dir = _resolve_ai_path(output_dir_value, base_dir=ai_project_dir)
    excel_path = _resolve_ai_path(excel_path_value, base_dir=ai_project_dir)

    pipeline_config = {
        "random_state": payload.get("random_state", 42),
        "n_synthetic_customers": payload.get("n_synthetic_customers", 1000),
        "n_personas": payload.get("n_personas", 7),
        "excel_path": str(excel_path),
        "output_dir": str(output_dir),
        "gemini_api_key": settings.GEMINI_API_KEY,
    }
    metadata = run_pipeline(pipeline_config)

    personas_path = Path(metadata["outputs"]["personas"])
    if not personas_path.exists():
        raise FileNotFoundError(f"Generated personas file not found: {personas_path}")

    personas = json.loads(personas_path.read_text(encoding="utf-8"))
    normalized_personas = store.replace_personas(
        project_id,
        personas,
        overwrite_existing=payload.get("overwrite_existing", True),
    )
    return {
        "resource": "personas",
        "project_id": project_id,
        "persona_count": len(normalized_personas),
        "artifacts": metadata.get("outputs", {}),
        "metadata": {
            "random_state": pipeline_config["random_state"],
            "n_synthetic_customers": pipeline_config["n_synthetic_customers"],
            "n_personas_requested": pipeline_config["n_personas"],
            "n_personas_generated": len(normalized_personas),
        },
    }
