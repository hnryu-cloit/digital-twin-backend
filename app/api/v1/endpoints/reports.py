from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user_id
from app.schemas.report import (
    ReportDetailResponse,
    ReportDownloadResponse,
    ReportGenerateRequest,
    ReportListResponse,
    ReportSummaryResponse,
)
from app.services.mock_store import store

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportSummaryResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(body: ReportGenerateRequest, _: str = Depends(get_current_user_id)):
    if body.project_id not in store.projects:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    report = store.create_report(body.project_id)
    return ReportSummaryResponse(**{key: report[key] for key in ("id", "project_id", "title", "type", "format", "size", "created_at")})


@router.get("", response_model=ReportListResponse)
async def list_reports(
    project_id: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = None,
    _: str = Depends(get_current_user_id),
):
    items = [report for report in store.reports.values() if report["project_id"] == project_id]
    if search:
        items = [item for item in items if search.lower() in item["title"].lower()]
    start = (page - 1) * size
    paged_items = items[start : start + size]
    summaries = [
        ReportSummaryResponse(**{key: item[key] for key in ("id", "project_id", "title", "type", "format", "size", "created_at")})
        for item in paged_items
    ]
    return ReportListResponse(items=summaries, page=page, size=size, total=len(items))


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(report_id: str, _: str = Depends(get_current_user_id)):
    report = store.reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return ReportDetailResponse(**report)


@router.get("/{report_id}/download", response_model=ReportDownloadResponse)
async def download_report(report_id: str, format: str = Query(default="pdf"), _: str = Depends(get_current_user_id)):
    if report_id not in store.reports:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return ReportDownloadResponse(
        report_id=report_id,
        format=format.upper(),
        download_url=f"https://download.digital-twin.local/reports/{report_id}.{format.lower()}",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
