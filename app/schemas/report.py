from datetime import datetime

from pydantic import BaseModel, Field


class ReportGenerateJobRequest(BaseModel):
    project_id: str
    report_type: str = Field(default="strategy")


class ReportSummaryResponse(BaseModel):
    id: str
    project_id: str
    title: str
    type: str
    format: str
    size: str
    created_at: datetime


class ReportGenerateRequest(BaseModel):
    project_id: str


class ReportDetailResponse(BaseModel):
    id: str
    project_id: str
    title: str
    sections: list[dict]
    kpis: list[dict]
    charts: list[dict]
    created_at: datetime


class ReportDownloadResponse(BaseModel):
    report_id: str
    format: str
    download_url: str
    expires_at: datetime


class ReportListResponse(BaseModel):
    items: list[ReportSummaryResponse]
    page: int
    size: int
    total: int
