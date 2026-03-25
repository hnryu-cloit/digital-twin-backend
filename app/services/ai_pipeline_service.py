from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.services.db_store import store

logger = logging.getLogger(__name__)


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
    cluster_personas = result.get("personas", [])

    # clustered_customers.parquet 경로 찾기 (AI 컨테이너 경로 → 백엔드 마운트 경로로 변환)
    artifacts = result.get("artifacts", {})
    clustered_path_raw = artifacts.get("clustered_data", "")
    personas_json_base = Path(settings.PERSONAS_JSON_PATH).parent  # e.g. /ai/output
    clustered_path = personas_json_base / "clustered_customers.parquet"
    if clustered_path_raw:
        # AI가 반환한 절대경로의 파일명만 사용
        clustered_path = personas_json_base / Path(clustered_path_raw).name

    individual_personas = _build_individual_personas(cluster_personas, clustered_path)
    personas_to_save = individual_personas if individual_personas else cluster_personas

    normalized_personas = store.replace_personas(
        project_id,
        personas_to_save,
        overwrite_existing=payload.get("overwrite_existing", True),
    )
    return {
        "resource": "personas",
        "project_id": project_id,
        "persona_count": len(normalized_personas),
        "artifacts": artifacts,
        "metadata": {
            "random_state": request_payload["random_state"],
            "n_synthetic_customers": request_payload["n_synthetic_customers"],
            "n_personas_requested": request_payload["n_personas"],
            "n_personas_generated": len(normalized_personas),
            "ai_service": settings.AI_SERVICE_BASE_URL,
            "pipeline": result.get("metadata", {}),
        },
    }


def _build_individual_personas(cluster_personas: list[dict], clustered_path: Path) -> list[dict]:
    """clustered_customers.parquet의 개별 고객을 페르소나 레코드로 변환."""
    try:
        import pandas as pd  # noqa: PLC0415

        if not clustered_path.exists():
            logger.warning("clustered_customers.parquet not found at %s", clustered_path)
            return []

        df = pd.read_parquet(clustered_path)
        if "persona_cluster" not in df.columns:
            logger.warning("persona_cluster column missing in parquet")
            return []

        # cluster_id → cluster persona 매핑
        cluster_map = {p["cluster_id"]: p for p in cluster_personas}

        # 클러스터별 인덱스 카운터
        cluster_counters: dict[int, int] = {}
        individual_personas: list[dict] = []

        for _, row in df.iterrows():
            cluster_id = int(row["persona_cluster"])
            cluster_persona = cluster_map.get(cluster_id)
            if cluster_persona is None:
                continue

            cluster_counters[cluster_id] = cluster_counters.get(cluster_id, 0) + 1
            n = cluster_counters[cluster_id]

            age = int(row.get("usr_age", 30))
            gender_raw = str(row.get("usr_gndr", "M")).strip().upper()
            gender = "여성" if gender_raw == "F" else "남성"

            # 개인 행동 점수로 클러스터 값에 약간의 변동 추가 (±10 범위)
            retention = float(row.get("retention_score", 0.7))
            purchase_intent = round(
                float(cluster_persona.get("purchase_intent", 70)) * (0.9 + retention * 0.2), 1
            )
            brand_attitude = round(
                float(cluster_persona.get("brand_attitude", 70)) * (0.9 + retention * 0.2), 1
            )

            individual_personas.append({
                "persona_name": f"{cluster_persona['persona_name']} #{n}",
                "persona_name_en": cluster_persona.get("persona_name_en", ""),
                "age_range": str(age),
                "gender": gender,
                "description": cluster_persona.get("description", ""),
                "key_characteristics": cluster_persona.get("key_characteristics", []),
                "purchase_intent": min(purchase_intent, 100.0),
                "brand_attitude": min(brand_attitude, 100.0),
                "marketing_acceptance": float(cluster_persona.get("marketing_acceptance", 70)),
                "future_value": float(cluster_persona.get("future_value", 70)),
                "preferred_channel": cluster_persona.get("preferred_channel", ""),
                "keywords": cluster_persona.get("keywords", []),
                "interests": cluster_persona.get("interests", []),
                "segment_tags": cluster_persona.get("segment_tags", []),
                "individual_stories": [],
            })

        logger.info("Built %d individual personas from parquet", len(individual_personas))
        return individual_personas

    except Exception as exc:
        logger.warning("Failed to build individual personas from parquet: %s", exc)
        return []


def import_excel_as_personas(project_id: str, overwrite: bool = True) -> dict[str, Any]:
    """Excel 실제 고객 데이터를 읽어서 DB에 페르소나로 저장."""
    import math

    try:
        import pandas as pd  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("pandas is required") from exc

    excel_path = Path(settings.AI_EXCEL_MOUNT_PATH)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    xl = pd.ExcelFile(str(excel_path))

    demo = xl.parse("Demo", header=1)
    clv = xl.parse("CLV", header=1)
    interests_df = xl.parse("관심사", header=1)

    # 고객별 관심사 top3 집계
    interests_map: dict[int, list[str]] = {}
    for _, row in interests_df.iterrows():
        idx = int(row["index"])
        score = float(row.get("INTEREST_SCORE", 0) or 0)
        cat = str(row.get("category", "")).strip()
        if cat:
            interests_map.setdefault(idx, [])
            interests_map[idx].append((score, cat))
    top_interests: dict[int, list[str]] = {
        idx: [c for _, c in sorted(cats, reverse=True)[:5]]
        for idx, cats in interests_map.items()
    }

    # Demo + CLV merge on index
    merged = demo.merge(clv, on="index", how="left", suffixes=("", "_clv"))

    # LTV 정규화를 위한 최대값
    ltv_max = float(merged["ltv_r"].max()) if "ltv_r" in merged.columns else 1.0
    val_max = float(merged["val_p"].max()) if "val_p" in merged.columns else 1.0

    personas: list[dict] = []
    for _, row in merged.iterrows():
        idx = int(row["index"])
        age = int(row.get("usr_age") or row.get("age") or 30)
        gndr = str(row.get("usr_gndr") or row.get("gender") or "M").strip().upper()
        gender = "여성" if gndr == "F" else "남성"
        region = str(row.get("usr_cnty_ap2", "") or "").strip()
        activeness = str(row.get("sa_activeness", "") or "").strip()

        # voyager_segment → segment / keywords
        seg_raw = row.get("voyager_segment", "")
        if isinstance(seg_raw, list):
            segments = [str(s).replace("np.str_('", "").replace("')", "").strip() for s in seg_raw]
        else:
            seg_str = str(seg_raw or "")
            segments = [s.strip().strip("'\"") for s in seg_str.strip("[]").split(",") if s.strip()] if seg_str else []
        segments = [s for s in segments if s and s != "nan"]
        primary_segment = segments[0] if segments else "General"

        # 점수 계산
        retention = float(row.get("retention_score") or 0.7)
        ltv = float(row.get("ltv_r") or 0)
        val = float(row.get("val_p") or 0)
        purchase_intent = round(min(retention * 100, 100), 1)
        brand_attitude = round(min(retention * 100, 100), 1)
        future_value = round(min((ltv / ltv_max) * 100, 100), 1) if ltv_max > 0 else 50.0
        marketing_acceptance = round(min((val / val_max) * 100, 100), 1) if val_max > 0 else 50.0

        product = str(row.get("product_mapping4", "") or "").strip()
        pchs_cnt = int(row.get("pchs_cnt") or 0)

        user_interests = top_interests.get(idx, [])

        personas.append({
            "persona_name": f"고객 #{idx:04d}",
            "persona_name_en": f"Customer #{idx:04d}",
            "age_range": str(age),
            "gender": gender,
            "description": f"{age}세 {gender} | {activeness} | {region}",
            "key_characteristics": [activeness] if activeness else [],
            "purchase_intent": purchase_intent,
            "brand_attitude": brand_attitude,
            "marketing_acceptance": marketing_acceptance,
            "future_value": future_value,
            "preferred_channel": "",
            "keywords": segments,
            "interests": user_interests,
            "segment_tags": [region] if region else [],
            "individual_stories": [],
            "purchase_history_hint": product,
            "purchase_count": pchs_cnt,
        })

    saved = store.replace_personas(project_id, personas, overwrite_existing=overwrite)
    return {
        "resource": "personas",
        "project_id": project_id,
        "persona_count": len(saved),
        "source": "excel",
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
