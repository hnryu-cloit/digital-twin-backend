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
        "gemini_model_name": payload.get("gemini_model_name", "gemini-3.0-flash"),
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


def run_survey_generation(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    endpoint = f"{settings.AI_SERVICE_BASE_URL.rstrip('/')}/internal/surveys/generate-draft"
    request_payload = {
        "job_id": payload.get("job_id"),
        "project_id": project_id,
        "user_prompt": payload.get("user_prompt", ""),
        "survey_type": payload.get("survey_type", "concept"),
        "question_count": payload.get("question_count", 5),
        "template": payload.get("template", {}),
        "segment_context": payload.get("segment_context", {}),
        "gemini_api_key": settings.GEMINI_API_KEY,
        "gemini_model_name": payload.get("gemini_model_name", "gemini-3-flash"),
    }
    try:
        with httpx.Client(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = client.post(endpoint, json=request_payload)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise RuntimeError(f"AI service request failed: {error}") from error

    result = response.json()
    questions = result.get("questions", [])
    stored = store.replace_survey_questions(project_id, questions)
    return {
        "resource": "survey_questions",
        "project_id": project_id,
        "question_count": len(stored),
        "metadata": result.get("metadata", {}),
    }


def run_report_generation(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    project = store.get_project(project_id)
    if project is None:
        raise ValueError("Project not found.")
    personas = store.list_personas(project_id)
    responses = store.get_response_feed(project_id, limit=1000)
    simulation = store.get_simulation(project_id) or {}
    keyword_items = store.get_response_keywords(project_id, limit=5)
    report_input = {
        "job_id": payload.get("job_id"),
        "project_id": project_id,
        "project_name": project["name"],
        "purpose": project.get("purpose", ""),
        "persona_count": len(personas),
        "response_count": len(responses),
        "target_responses": project.get("target_responses", 0),
        "response_progress": simulation.get("progress", project.get("progress", 0)),
        "dominant_segment": "데이터 없음",
        "top_question": "집계 중",
        "keyword_items": keyword_items,
        "age_buckets": [],
        "segment_cards": [],
        "question_strength_data": [],
        "detailed_distribution": [],
        "gemini_api_key": settings.GEMINI_API_KEY,
        "gemini_model_name": payload.get("gemini_model_name", "gemini-3-flash"),
    }

    if personas:
        segment_counts: dict[str, int] = {}
        age_buckets = {"20대": 0, "30대": 0, "40대": 0, "50대+": 0}
        segment_groups: dict[str, list[dict[str, Any]]] = {}
        for persona in personas:
            segment = persona.get("segment") or "미분류"
            segment_counts[segment] = segment_counts.get(segment, 0) + 1
            segment_groups.setdefault(segment, []).append(persona)
            age = persona.get("age", 0)
            if age < 30:
                age_buckets["20대"] += 1
            elif age < 40:
                age_buckets["30대"] += 1
            elif age < 50:
                age_buckets["40대"] += 1
            else:
                age_buckets["50대+"] += 1
        report_input["dominant_segment"] = max(segment_counts.items(), key=lambda item: item[1])[0]
        highest = max(age_buckets.values(), default=1) or 1
        report_input["age_buckets"] = [
            {"name": name, "value": value, "benchmark": highest}
            for name, value in age_buckets.items()
        ]
        segment_cards = []
        for segment_name, members in sorted(segment_groups.items(), key=lambda item: len(item[1]), reverse=True)[:3]:
            def top_value(key: str) -> str:
                counts: dict[str, int] = {}
                for member in members:
                    value = member.get(key) or "데이터 없음"
                    counts[value] = counts.get(value, 0) + 1
                return max(counts.items(), key=lambda item: item[1])[0]
            segment_cards.append(
                {
                    "segment": segment_name,
                    "count": len(members),
                    "share": round((len(members) / len(personas)) * 100, 1) if personas else 0.0,
                    "buyChannel": top_value("buy_channel"),
                    "productGroup": top_value("product_group"),
                    "region": top_value("region"),
                }
            )
        report_input["segment_cards"] = segment_cards

    if responses:
        question_counts: dict[str, int] = {}
        for response_item in responses:
            key = response_item.get("question_text") or response_item.get("question_id") or "집계 중"
            question_counts[key] = question_counts.get(key, 0) + 1
        report_input["top_question"] = max(question_counts.items(), key=lambda item: item[1])[0]

    questions = store.list_survey_questions(project_id)
    question_strength_data = []
    detailed_distribution = []
    for question in questions[:7]:
        distribution = store.get_response_distribution(project_id, question["id"])
        top_value = max((item["value"] for item in distribution), default=0)
        question_strength_data.append({"label": question["id"], "value": top_value})
        if distribution:
            detailed_distribution.append(
                {
                    "question_id": question["id"],
                    "question_text": question["text"],
                    "distribution": distribution,
                }
            )
    report_input["question_strength_data"] = question_strength_data
    report_input["detailed_distribution"] = detailed_distribution

    endpoint = f"{settings.AI_SERVICE_BASE_URL.rstrip('/')}/internal/reports/generate"
    try:
        with httpx.Client(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = client.post(endpoint, json=report_input)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise RuntimeError(f"AI service request failed: {error}") from error

    result = response.json()
    report = result.get("report", {})
    stored = store.create_report_from_payload(project_id, report)
    return {
        "resource": "report",
        "project_id": project_id,
        "report_id": stored["id"],
        "metadata": result.get("metadata", {}),
    }
