"""
GET /api/data/export?table=<name>
AI 파이프라인이 모델링 시 호출해 고객 데이터를 가져가는 엔드포인트.
data/ 디렉터리의 CSV를 읽어 JSON으로 반환한다.
"""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"

ALLOWED_TABLES = {"demo", "clv", "purchase", "owned", "app_usage", "interests", "rewards"}

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/export")
async def export_table(
    table: str = Query(..., description="테이블명: demo | clv | purchase | owned | app_usage | interests | rewards"),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown table '{table}'. Allowed: {sorted(ALLOWED_TABLES)}",
        )

    csv_path = DATA_DIR / f"{table}.csv"
    if not csv_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data file not found: {csv_path.name}. Run scripts/generate_dummy_data.py first.",
        )

    df = pd.read_csv(csv_path)
    return {"table": table, "total": len(df), "columns": list(df.columns), "records": df.where(df.notna(), None).to_dict(orient="records")}


@router.get("/tables")
async def list_tables():
    """사용 가능한 테이블 목록과 row 수 반환."""
    result = {}
    for table in sorted(ALLOWED_TABLES):
        csv_path = DATA_DIR / f"{table}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path, nrows=0)
            # row count without loading all data
            with open(csv_path) as f:
                row_count = sum(1 for _ in f) - 1
            result[table] = {"rows": row_count, "columns": len(df.columns), "available": True}
        else:
            result[table] = {"available": False}
    return result