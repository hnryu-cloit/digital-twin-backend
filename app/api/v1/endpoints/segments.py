from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user_id
from app.schemas.segment import (
    FilterOptionItem,
    SegmentDistributionItem,
    SegmentFilterOptionsResponse,
    SegmentFilterRequest,
    SegmentKpiResponse,
)
from app.services.db_store import store

router = APIRouter(prefix="/segments", tags=["segments"])

SEGMENT_COLORS = ["#2F66FF", "#5A8BFF", "#88ABFF", "#B6CAFF", "#DCE6FF"]


def _build_option_items(values: list[str]) -> list[FilterOptionItem]:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1

    total = sum(counts.values())
    return [
        FilterOptionItem(
            label=label,
            count=count,
            ratio=round((count / total) * 100, 1) if total else 0.0,
        )
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _resolve_project_id(project_id: str | None) -> str | None:
    if project_id:
        return project_id
    projects = store.list_projects()
    return projects[0]["id"] if projects else None


def _compute_change_rate(personas: list[dict]) -> float:
    if not personas:
        return 0.0
    purchase_avg = sum(item["purchase_intent"] for item in personas) / len(personas)
    brand_avg = sum(item["brand_attitude"] for item in personas) / len(personas)
    return round(purchase_avg - brand_avg, 1)


@router.post("/aggregate", response_model=list[SegmentDistributionItem])
async def aggregate_segments(body: SegmentFilterRequest, _: str = Depends(get_current_user_id)):
    project_id = _resolve_project_id(body.project_id)
    if not project_id:
        return []
    personas = store.list_personas(project_id)
    if body.segments:
        personas = [persona for persona in personas if persona["segment"] in body.segments]

    counts: dict[str, int] = {}
    for persona in personas:
        counts[persona["segment"]] = counts.get(persona["segment"], 0) + 1

    total = sum(counts.values())
    items = []
    for index, (label, count) in enumerate(counts.items()):
        ratio = round((count / total) * 100, 1) if total else 0.0
        items.append(SegmentDistributionItem(label=label, count=count, ratio=ratio, color=SEGMENT_COLORS[index % len(SEGMENT_COLORS)]))
    return items


@router.post("/chart", response_model=list[SegmentDistributionItem])
async def get_segment_chart(body: SegmentFilterRequest, user_id: str = Depends(get_current_user_id)):
    return await aggregate_segments(body, user_id)


@router.post("/kpi", response_model=SegmentKpiResponse)
async def get_segment_kpis(body: SegmentFilterRequest, _: str = Depends(get_current_user_id)):
    project_id = _resolve_project_id(body.project_id)
    if not project_id:
        return SegmentKpiResponse(
            total_personas=0,
            average_purchase_intent=0.0,
            marketing_acceptance=0.0,
            brand_preference=0.0,
            change_rate=0.0,
        )
    personas = store.list_personas(project_id)
    if body.segments:
        personas = [persona for persona in personas if persona["segment"] in body.segments]

    total = len(personas)
    if total == 0:
        return SegmentKpiResponse(
            total_personas=0,
            average_purchase_intent=0.0,
            marketing_acceptance=0.0,
            brand_preference=0.0,
            change_rate=0.0,
        )

    return SegmentKpiResponse(
        total_personas=total,
        average_purchase_intent=round(sum(item["purchase_intent"] for item in personas) / total, 1),
        marketing_acceptance=round(sum(item["marketing_acceptance"] for item in personas) / total, 1),
        brand_preference=round(sum(item["brand_attitude"] for item in personas) / total, 1),
        change_rate=_compute_change_rate(personas),
    )


@router.get("/filter-options", response_model=SegmentFilterOptionsResponse)
async def get_segment_filter_options(
    project_id: str | None = Query(default=None),
    _: str = Depends(get_current_user_id),
):
    resolved_project_id = _resolve_project_id(project_id)
    personas = store.list_personas(resolved_project_id) if resolved_project_id else []
    return SegmentFilterOptionsResponse(
        occupations=_build_option_items([persona["occupation_category"] for persona in personas]),
        regions=_build_option_items([persona["region"] for persona in personas]),
        households=_build_option_items([persona["household_type"] for persona in personas]),
        buy_channels=_build_option_items([persona["buy_channel"] for persona in personas]),
        content_channels=_build_option_items([persona["preferred_channel"] for persona in personas]),
        product_groups=_build_option_items([persona["product_group"] for persona in personas]),
    )
