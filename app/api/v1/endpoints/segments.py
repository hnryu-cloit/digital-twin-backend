from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.segment import SegmentDistributionItem, SegmentFilterRequest, SegmentKpiResponse
from app.services.db_store import store

router = APIRouter(prefix="/segments", tags=["segments"])

SEGMENT_COLORS = ["#2F66FF", "#5A8BFF", "#88ABFF", "#B6CAFF", "#DCE6FF"]


@router.post("/aggregate", response_model=list[SegmentDistributionItem])
async def aggregate_segments(body: SegmentFilterRequest, _: str = Depends(get_current_user_id)):
    personas = store.list_personas("prj-001")
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
    personas = store.list_personas("prj-001")
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
        change_rate=4.8,
    )
