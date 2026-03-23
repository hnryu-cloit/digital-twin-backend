from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
from app.services.db_store import store

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("/control", response_model=SimulationControlResponse)
async def control_simulation(body: SimulationControlRequest, _: str = Depends(get_current_user_id)):
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
async def get_distribution(question_id: str, _: str = Depends(get_current_user_id)):
    mapping = {
        "q-001": [
            {"label": "매우 잘 안다", "value": 41.0},
            {"label": "어느 정도 안다", "value": 32.0},
            {"label": "들어봤다", "value": 18.0},
            {"label": "잘 모른다", "value": 9.0},
        ],
        "q-002": [
            {"label": "매우 크다", "value": 45.0},
            {"label": "크다", "value": 30.0},
            {"label": "보통", "value": 15.0},
            {"label": "낮다", "value": 7.0},
            {"label": "매우 낮다", "value": 3.0},
        ],
    }
    return [ResponseDistributionItem(**item) for item in mapping.get(question_id, [])]


@router.get("/insight", response_model=InsightResponse)
async def get_insight(question_id: str, _: str = Depends(get_current_user_id)):
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