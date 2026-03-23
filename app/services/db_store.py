"""SQLite-backed store — same interface as MockStore but persists to DB."""
from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.security import hash_password
from app.services.db_models import (
    Base,
    PersonaModel,
    ProjectModel,
    ReportModel,
    RevokedTokenModel,
    SimulationModel,
    SimulationResponseModel,
    SurveyQuestionModel,
    UserModel,
)

# ── Engine (sync SQLite) ──────────────────────────────────────────────────────
_db_url = settings.DATABASE_URL
# aiosqlite URL → sync URL
if _db_url.startswith("sqlite+aiosqlite"):
    _db_url = _db_url.replace("sqlite+aiosqlite", "sqlite", 1)

engine = create_engine(_db_url, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create all tables. Called on app startup."""
    Base.metadata.create_all(bind=engine)
    _seed_admin()


def _seed_admin() -> None:
    """Ensure admin user exists."""
    with SessionLocal() as session:
        existing = session.query(UserModel).filter_by(id="usr-admin").first()
        if existing:
            return
        admin = UserModel(
            id="usr-admin",
            email=settings.DEFAULT_ADMIN_EMAIL,
            hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            name=settings.DEFAULT_ADMIN_NAME,
            role="admin",
            is_active=True,
        )
        session.add(admin)
        session.commit()


# ── Helper ────────────────────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_persona_response(persona_dict: dict) -> dict:
    """Compute derived score fields from raw persona data."""
    activity_logs = persona_dict.get("activity_logs", [])
    brand_attitude = persona_dict.get("brand_attitude", 0.0)
    marketing_acceptance = persona_dict.get("marketing_acceptance", 0.0)
    purchase_intent = persona_dict.get("purchase_intent", 0.0)

    data_confidence = round(min(99.0, 55.0 + (len(activity_logs) * 12.5)), 1)
    churn_risk = round(
        max(1.0, 100 - ((brand_attitude * 0.45) + (marketing_acceptance * 0.35) + (purchase_intent * 0.20))),
        1,
    )
    engagement_score = round((marketing_acceptance * 0.6) + (purchase_intent * 0.4), 1)
    return {
        **{k: v for k, v in persona_dict.items() if k not in ("profile", "purchase_history", "activity_logs", "cot")},
        "score": {
            "churn_risk": churn_risk,
            "engagement_score": engagement_score,
            "future_value": persona_dict.get("future_value", 0.0),
            "data_confidence": data_confidence,
        },
    }


# ── Store ─────────────────────────────────────────────────────────────────────
class DbStore:
    """Persistent SQLite store with the same public API as MockStore."""

    # ── prompts / llm settings (in-memory only; not critical to persist) ──────
    def __init__(self) -> None:
        self.prompts = {
            "simulation": "Respond as a market research digital twin.",
            "survey": "Generate concise and structured survey questions.",
            "assistant": "Answer with evidence and confidence.",
        }
        self.llm_parameters = {"temperature": 0.7, "top_p": 0.9}
        self.chat_sessions: dict[str, list[dict]] = {}

    # ── Users ─────────────────────────────────────────────────────────────────
    def get_user(self, user_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            user = session.query(UserModel).filter_by(id=user_id).first()
            return user.to_dict() if user else None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        with SessionLocal() as session:
            user = session.query(UserModel).filter_by(email=email).first()
            return user.to_dict() if user else None

    # ── Revoked tokens ────────────────────────────────────────────────────────
    def is_token_revoked(self, token: str) -> bool:
        with SessionLocal() as session:
            return session.query(RevokedTokenModel).filter_by(token=token).first() is not None

    def revoke_token(self, token: str) -> None:
        with SessionLocal() as session:
            if not session.query(RevokedTokenModel).filter_by(token=token).first():
                session.add(RevokedTokenModel(token=token, revoked_at=_now()))
                session.commit()

    # ── Projects ──────────────────────────────────────────────────────────────
    def get_project(self, project_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            if proj is None or proj.deleted_at is not None:
                return None
            return proj.to_dict()

    def list_projects(self) -> list[dict]:
        with SessionLocal() as session:
            projs = session.query(ProjectModel).filter(ProjectModel.deleted_at == None).all()
            return [p.to_dict() for p in projs]

    def create_project(self, payload: dict, user_id: str) -> dict:
        now = _now()
        project_id = f"prj-{uuid.uuid4().hex[:8]}"
        with SessionLocal() as session:
            proj = ProjectModel(
                id=project_id,
                name=payload["name"],
                type=payload["type"],
                purpose=payload["purpose"],
                description=payload.get("description"),
                data_sources=payload.get("data_sources", []),
                tags=payload.get("tags", []),
                status="draft",
                progress=0,
                response_count=0,
                target_responses=payload["target_responses"],
                surveys_count=0,
                reports_count=0,
                persona_count=0,
                created_by=user_id,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
            session.add(proj)
            session.commit()
            return proj.to_dict()

    def update_project(self, project_id: str, payload: dict) -> Optional[dict]:
        with SessionLocal() as session:
            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            if proj is None or proj.deleted_at is not None:
                return None
            for key in ("name", "description", "tags"):
                if key in payload and payload[key] is not None:
                    setattr(proj, key, payload[key])
            proj.updated_at = _now()
            session.commit()
            return proj.to_dict()

    def soft_delete_project(self, project_id: str) -> bool:
        with SessionLocal() as session:
            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            if proj is None or proj.deleted_at is not None:
                return False
            proj.deleted_at = _now()
            session.commit()
            return True

    def _touch_project(self, session: Session, project_id: str) -> None:
        proj = session.query(ProjectModel).filter_by(id=project_id).first()
        if proj:
            proj.updated_at = _now()

    # ── Personas ──────────────────────────────────────────────────────────────
    def list_personas(self, project_id: str) -> list[dict]:
        with SessionLocal() as session:
            personas = session.query(PersonaModel).filter_by(project_id=project_id).all()
            return [_build_persona_response(p.to_dict()) for p in personas]

    def create_persona_pool(self, payload: dict) -> list[dict]:
        created: list[dict] = []
        with SessionLocal() as session:
            for index in range(payload["size"]):
                persona_id = f"prs-{uuid.uuid4().hex[:8]}"
                age = 25 + (index % 15)
                purchase_intent = float(60 + (index % 30))
                marketing_acceptance = float(55 + (index % 35))
                brand_attitude = float(58 + (index % 28))
                future_value = round(
                    (purchase_intent * 0.45) + (marketing_acceptance * 0.35) + (brand_attitude * 0.2), 1
                )
                p = PersonaModel(
                    id=persona_id,
                    project_id=payload["project_id"],
                    name=f"{payload['segment']} Persona {index + 1}",
                    age=age,
                    gender=payload["gender"],
                    occupation=payload["occupation"],
                    segment=payload["segment"],
                    keywords=[payload["segment"], payload["occupation"], "AI"],
                    interests=["브랜드 탐색", "제품 비교", "온라인 리뷰"],
                    preferred_channel="YouTube",
                    purchase_intent=purchase_intent,
                    marketing_acceptance=marketing_acceptance,
                    brand_attitude=brand_attitude,
                    future_value=future_value,
                    profile=f"{payload['segment']} 조건을 기반으로 생성된 디지털 트윈 페르소나",
                    purchase_history=["Galaxy S24"],
                    activity_logs=["세그먼트 기반 생성"],
                    cot=["세그먼트 조건 적용", "기본 점수 생성", "채널 선호 계산"],
                )
                session.add(p)
                created.append(_build_persona_response(p.to_dict()))

            proj = session.query(ProjectModel).filter_by(id=payload["project_id"]).first()
            if proj:
                proj.persona_count = (proj.persona_count or 0) + len(created)
                proj.updated_at = _now()
            session.commit()
        return created

    def get_persona_detail(self, persona_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            p = session.query(PersonaModel).filter_by(id=persona_id).first()
            if p is None:
                return None
            d = p.to_dict()
            return {**_build_persona_response(d), "profile": d["profile"], "purchase_history": d["purchase_history"], "activity_logs": d["activity_logs"], "cot": d["cot"]}

    # ── Surveys ───────────────────────────────────────────────────────────────
    def list_survey_questions(self, project_id: str) -> list[dict]:
        with SessionLocal() as session:
            qs = (
                session.query(SurveyQuestionModel)
                .filter_by(project_id=project_id)
                .order_by(SurveyQuestionModel.order)
                .all()
            )
            return [q.to_dict() for q in qs]

    def replace_survey_questions(self, project_id: str, questions: list[dict]) -> list[dict]:
        with SessionLocal() as session:
            session.query(SurveyQuestionModel).filter_by(project_id=project_id).delete()
            for index, question in enumerate(questions, start=1):
                question["order"] = index
                session.add(
                    SurveyQuestionModel(
                        id=question["id"],
                        project_id=project_id,
                        text=question["text"],
                        type=question["type"],
                        options=question.get("options", []),
                        order=index,
                        status=question.get("status", "draft"),
                    )
                )
            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            if proj:
                proj.surveys_count = 1 if questions else 0
                proj.updated_at = _now()
            session.commit()
        return deepcopy(questions)

    # ── Simulations ───────────────────────────────────────────────────────────
    def get_simulation(self, project_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            sim = session.query(SimulationModel).filter_by(project_id=project_id).first()
            return sim.to_dict() if sim else None

    def save_simulation(self, project_id: str, data: dict) -> None:
        with SessionLocal() as session:
            sim = session.query(SimulationModel).filter_by(project_id=project_id).first()
            if sim is None:
                sim = SimulationModel(project_id=project_id)
                session.add(sim)
            sim.job_id = data.get("job_id", f"job-{project_id}")
            sim.status = data.get("status", "idle")
            sim.progress = data.get("progress", 0)
            sim.completed_responses = data.get("completed_responses", 0)
            sim.target_responses = data.get("target_responses", 0)
            session.commit()

    def get_response_feed(self, project_id: str, limit: int = 20) -> list[dict]:
        with SessionLocal() as session:
            responses = (
                session.query(SimulationResponseModel)
                .filter_by(project_id=project_id)
                .order_by(SimulationResponseModel.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [r.to_dict() for r in responses]

    def get_response_by_id(self, response_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            r = session.query(SimulationResponseModel).filter_by(id=response_id).first()
            return r.to_dict() if r else None

    # ── Reports ───────────────────────────────────────────────────────────────
    def get_report(self, report_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            r = session.query(ReportModel).filter_by(id=report_id).first()
            return r.to_dict() if r else None

    def list_reports(self, project_id: str, search: Optional[str] = None) -> list[dict]:
        with SessionLocal() as session:
            q = session.query(ReportModel).filter_by(project_id=project_id)
            if search:
                q = q.filter(ReportModel.title.ilike(f"%{search}%"))
            return [r.to_dict() for r in q.all()]

    def create_report(self, project_id: str) -> dict:
        report_id = f"rpt-{uuid.uuid4().hex[:8]}"
        now = _now()
        with SessionLocal() as session:
            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            project_name = proj.name if proj else project_id

            report = ReportModel(
                id=report_id,
                project_id=project_id,
                title=f"{project_name} 리포트",
                type="strategy",
                format="PDF",
                size="4.2MB",
                created_at=now,
                sections=[
                    {"id": "overview", "title": "개요", "content": "시뮬레이션 결과 기반 자동 생성 리포트입니다."},
                    {"id": "recommendation", "title": "권장사항", "content": "핵심 타겟 중심 메시지 전략을 추천합니다."},
                ],
                kpis=[{"label": "응답률", "value": "64%"}, {"label": "구매 의향", "value": "68.7%"}],
                charts=[{"id": "chart-01", "type": "bar", "title": "응답 분포"}],
            )
            session.add(report)
            if proj:
                proj.reports_count = (proj.reports_count or 0) + 1
                proj.updated_at = now
            session.commit()
            return report.to_dict()


store = DbStore()