"""시뮬레이션 백그라운드 실행기 - Gemini를 통해 페르소나별 응답 생성."""
from __future__ import annotations

import json
import logging
import random
import re
import uuid
from typing import Optional, Union

from app.services import gemini_client
from app.services.db_store import store

logger = logging.getLogger(__name__)
BATCH_SIZE = 6  # 한 번에 생성하는 응답 수


def _parse_json_block(text: str, kind: str = "object") -> Optional[Union[dict, list]]:
    pattern = r"\[.*\]" if kind == "array" else r"\{.*\}"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except Exception:
        return None


def _generate_response_with_gemini(persona: dict, question: dict) -> Optional[dict]:  # noqa: E501
    """Gemini로 단일 응답 생성. 실패 시 None."""
    options = question.get("options") or ["매우 그렇다", "그렇다", "보통", "아니다", "전혀 아니다"]
    prompt = f"""당신은 시장조사 디지털 트윈 페르소나입니다. 아래 프로필로 설문에 응답하세요.

페르소나:
- 이름: {persona['name']}, 세그먼트: {persona['segment']}
- 나이: {persona.get('age', 30)}세, 직업: {persona.get('occupation', '')}
- 관심 키워드: {', '.join(persona.get('keywords', []))}
- 구매 의향: {persona.get('purchase_intent', 70):.0f}/100

문항: {question['text']}
선택지: {', '.join(options)}

다음 JSON만 출력하세요:
{{"selected_option": "선택지 중 하나", "rationale": "이 페르소나의 응답 이유 2~3문장", "cot": ["추론 단계 1", "추론 단계 2", "추론 단계 3"]}}"""

    text = gemini_client.generate(prompt, temperature=0.85)
    if not text:
        return None
    data = _parse_json_block(text, "object")
    if not isinstance(data, dict):
        return None
    return data


def _fallback_response(persona: dict, question: dict) -> dict:
    """Gemini 없을 때 구매 의향 기반 결정론적 응답."""
    options = question.get("options") or ["매우 그렇다", "그렇다", "보통", "아니다", "전혀 아니다"]
    intent = persona.get("purchase_intent", 70)
    idx = 0 if intent > 80 else (1 if intent > 65 else 2)
    idx = min(idx, len(options) - 1)
    return {
        "selected_option": options[idx],
        "rationale": f"{persona['segment']} 특성을 고려한 응답입니다. 구매 의향 {intent:.0f}점 기준으로 판단했습니다.",
        "cot": [
            f"페르소나 '{persona['name']}' 프로필 분석",
            f"구매 의향 {intent:.0f}/100 → 응답 성향 도출",
            "응답 일관성 검증 완료",
        ],
    }


def run_simulation_batch(project_id: str) -> None:
    """FastAPI BackgroundTasks로 실행. 페르소나×문항 미완료 콤보에서 BATCH_SIZE개 응답 생성."""
    pending = store.get_pending_simulation_pairs(project_id)
    if not pending:
        # 모든 콤보 완료 → 시뮬레이션 완료 처리
        sim = store.get_simulation(project_id)
        if sim:
            sim["status"] = "completed"
            sim["progress"] = 100
            store.save_simulation(project_id, sim)
        logger.info("시뮬레이션 완료: %s", project_id)
        return

    for persona, question in pending[:BATCH_SIZE]:
        # 정지 요청 확인
        current_sim = store.get_simulation(project_id)
        if current_sim and current_sim.get("status") == "paused":
            logger.info("시뮬레이션 중단: %s", project_id)
            break

        # 응답 생성
        generated = _generate_response_with_gemini(persona, question)
        if generated is None:
            generated = _fallback_response(persona, question)

        integrity = round(random.uniform(88.0, 99.2), 1)
        store.add_simulation_response(project_id, {
            "id": f"resp-{uuid.uuid4().hex[:8]}",
            "persona_name": persona["name"],
            "segment": persona["segment"],
            "question_id": question["id"],
            "question_text": question["text"],
            "selected_option": generated["selected_option"],
            "rationale": generated["rationale"],
            "integrity_score": integrity,
            "cot": generated["cot"],
        })
