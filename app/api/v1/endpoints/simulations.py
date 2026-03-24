import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user_id
from app.schemas.simulation import (
    CotResponse,
    InsightResponse,
    KeywordTrendItem,
    ResponseDistributionItem,
    ResponseFeedItem,
    SimulationControlRequest,
    SimulationControlResponse,
    SimulationProgressResponse,
)
from app.services import gemini_client
from app.services.db_store import store
from app.services.simulation_runner import run_simulation_batch

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("/control", response_model=SimulationControlResponse)
async def control_simulation(
    body: SimulationControlRequest,
    background_tasks: BackgroundTasks,
    _: str = Depends(get_current_user_id),
):
    project = store.get_project(body.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    simulation = store.get_simulation(body.project_id) or {
        "job_id": f"job-{body.project_id}",
        "status": "idle",
        "progress": 0,
        "completed_responses": 0,
        "target_responses": project["target_responses"],
    }
    if body.action == "start":
        simulation["status"] = "running"
        simulation["progress"] = max(simulation["progress"], 5)
        background_tasks.add_task(run_simulation_batch, body.project_id)
    elif body.action == "stop":
        simulation["status"] = "paused"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be start or stop.")

    store.save_simulation(body.project_id, simulation)
    return SimulationControlResponse(
        job_id=simulation["job_id"],
        status=simulation["status"],
        progress=simulation["progress"],
    )


@router.get("/progress", response_model=SimulationProgressResponse)
async def get_progress(project_id: str, _: str = Depends(get_current_user_id)):
    simulation = store.get_simulation(project_id)
    if simulation is None:
        project = store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        return SimulationProgressResponse(
            project_id=project_id,
            job_id=None,
            completed_responses=0,
            target_responses=project["target_responses"],
            progress=0,
        )
    return SimulationProgressResponse(project_id=project_id, **simulation)


@router.get("/feed", response_model=list[ResponseFeedItem])
async def get_feed(project_id: str, limit: int = Query(default=20, ge=1, le=100), _: str = Depends(get_current_user_id)):
    return [ResponseFeedItem(**item) for item in store.get_response_feed(project_id, limit)]


@router.get("/distribution", response_model=list[ResponseDistributionItem])
async def get_distribution(
    project_id: str,
    question_id: str,
    _: str = Depends(get_current_user_id),
):
    data = store.get_response_distribution(project_id, question_id)
    if data:
        return [ResponseDistributionItem(**item) for item in data]
    # 데이터 없으면 빈 리스트 반환
    return []


@router.get("/insight", response_model=InsightResponse)
async def get_insight(
    project_id: str,
    question_id: str,
    _: str = Depends(get_current_user_id),
):
    # Gemini로 실제 인사이트 생성 시도
    if gemini_client.is_available():
        try:
            distribution = store.get_response_distribution(project_id, question_id)
            questions = store.list_survey_questions(project_id)
            question_text = next(
                (q["text"] for q in questions if q["id"] == question_id),
                question_id,
            )
            dist_summary = ", ".join(
                f"{item['label']}: {item['value']}%" for item in distribution
            ) if distribution else "데이터 없음"
            prompt = f"""다음 설문 문항과 응답 분포 데이터를 분석하여 마케팅 인사이트를 생성하세요.

문항: {question_text}
응답 분포: {dist_summary}

다음 JSON만 출력하세요:
{{"summary": "핵심 인사이트 1~2문장", "strategies": ["전략 1", "전략 2", "전략 3"]}}"""

            text = gemini_client.generate(prompt, temperature=0.7)
            if text:
                pattern = r"\{.*\}"
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, dict) and "summary" in parsed and "strategies" in parsed:
                        return InsightResponse(
                            summary=parsed["summary"],
                            strategies=parsed["strategies"],
                            cached_until=datetime.now(timezone.utc) + timedelta(minutes=15),
                        )
        except Exception:
            pass

    # 폴백
    return InsightResponse(
        summary=f"{question_id} 기준으로 구매 전환 가능성이 높은 세그먼트가 확인되었습니다.",
        strategies=[
            "핵심 타겟 메시지를 사용 장면 중심으로 전환합니다.",
            "야간 촬영 및 AI 자동 보정 비교 자산을 전면 배치합니다.",
        ],
        cached_until=datetime.now(timezone.utc) + timedelta(minutes=15),
    )


@router.get("/keywords", response_model=list[KeywordTrendItem])
async def get_keywords(project_id: str, _: str = Depends(get_current_user_id)):
    data = store.get_response_keywords(project_id)
    if data:
        return [KeywordTrendItem(**item) for item in data]
    # 기존 하드코딩 폴백
    return [
        KeywordTrendItem(keyword="야간 촬영", frequency=74, trend="up"),
        KeywordTrendItem(keyword="자동 보정", frequency=69, trend="up"),
        KeywordTrendItem(keyword="가격 부담", frequency=31, trend="down"),
    ]


@router.get("/cot/{response_id}", response_model=CotResponse)
async def get_cot(response_id: str, _: str = Depends(get_current_user_id)):
    item = store.get_response_by_id(response_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found.")
    return CotResponse(
        response_id=response_id,
        integrity_score=item["integrity_score"],
        steps=item["cot"],
        meta={"persona_name": item["persona_name"], "segment": item["segment"]},
    )