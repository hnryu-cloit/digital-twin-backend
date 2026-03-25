"""SQLite-backed store — same interface as MockStore but persists to DB."""
from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.defaults import DEFAULT_LLM_PARAMETERS, DEFAULT_PROMPTS
from app.core.security import hash_password
from app.services.db_migrations import ensure_sqlite_persona_dimensions, ensure_sqlite_survey_question_metadata
from app.services.db_models import (
    AIJobModel,
    Base,
    PersonaModel,
    ProjectModel,
    ReportModel,
    RevokedTokenModel,
    SettingModel,
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


def _run_sqlite_migrations() -> None:
    if _db_url.startswith("sqlite"):
        sqlite_path = _db_url.replace("sqlite:///", "", 1)
        ensure_sqlite_persona_dimensions(sqlite_path)
        ensure_sqlite_survey_question_metadata(sqlite_path)


_run_sqlite_migrations()


def init_db() -> None:
    """Create all tables. Called on app startup."""
    Base.metadata.create_all(bind=engine)
    _run_sqlite_migrations()
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


def _derive_occupation_category(occupation: str, age: int) -> str:
    occupation_lower = occupation.lower()
    if age <= 24:
        return "학생"
    if any(keyword in occupation_lower for keyword in ("개발", "디자인", "연구", "컨설턴트", "architect")):
        return "전문직"
    if any(keyword in occupation_lower for keyword in ("사업", "자영업", "대표")):
        return "자영업자"
    if any(keyword in occupation_lower for keyword in ("프리랜서", "유튜버", "크리에이터")):
        return "프리랜서"
    return "직장인"


def _derive_region(age: int, segment: str) -> str:
    if "비즈니스" in segment or age >= 40:
        return "대한민국"
    if "게이밍" in segment:
        return "일본"
    if "프리미엄" in segment:
        return "미국"
    return "대한민국"


def _derive_household_type(age: int, segment: str) -> str:
    if age <= 24:
        return "1인 가구"
    if "실용 중시 가족형" in segment:
        return "3인 이상"
    if age >= 38:
        return "2인 가구"
    return "1인 가구"


def _derive_buy_channel(preferred_channel: str) -> str:
    channel_map = {
        "YouTube": "자급제",
        "Instagram": "공식몰",
        "TikTok": "통신사 대리점",
        "LinkedIn": "오프라인 유통",
    }
    return channel_map.get(preferred_channel, "공식몰")


def _derive_product_group(purchase_history: list[str]) -> str:
    device = " ".join(purchase_history).lower()
    if "fold" in device:
        return "Galaxy Z Fold"
    if "flip" in device:
        return "Galaxy Z Flip"
    if "ultra" in device:
        return "Galaxy S Ultra"
    if "s24+" in device or "s23+" in device:
        return "Galaxy S Plus"
    if "a55" in device or "a34" in device or "a35" in device:
        return "Galaxy A"
    return "Galaxy S"


def _parse_age_range(age_range: str) -> int:
    numbers = [int(part) for part in age_range.replace("~", "-").split("-") if part.strip().isdigit()]
    if len(numbers) >= 2:
        return round((numbers[0] + numbers[1]) / 2)
    if len(numbers) == 1:
        return numbers[0]
    return 30


def _infer_gender(description: str) -> str:
    if "남성" in description:
        return "남성"
    if "여성" in description:
        return "여성"
    return "혼합"


def _infer_purchase_history(persona: dict) -> list[str]:
    combined = " ".join(
        [
            persona.get("persona_name", ""),
            persona.get("description", ""),
            " ".join(persona.get("keywords", [])),
            " ".join(persona.get("interests", [])),
        ]
    ).lower()
    if "fold" in combined or "폴드" in combined:
        return ["Galaxy Z Fold6"]
    if "flip" in combined or "플립" in combined:
        return ["Galaxy Z Flip6"]
    if "premium" in combined or "프리미엄" in combined or "고성능" in combined or "ultra" in combined:
        return ["Galaxy S24 Ultra"]
    if "실용" in combined or "balance" in combined or "밸런스" in combined:
        return ["Galaxy A55"]
    return ["Galaxy S24"]


def _build_persona_response(persona_dict: dict) -> dict:
    """Compute derived score fields from raw persona data."""
    activity_logs = persona_dict.get("activity_logs", [])
    brand_attitude = persona_dict.get("brand_attitude", 0.0)
    marketing_acceptance = persona_dict.get("marketing_acceptance", 0.0)
    purchase_intent = persona_dict.get("purchase_intent", 0.0)
    age = persona_dict.get("age", 0)
    occupation = persona_dict.get("occupation", "")
    segment = persona_dict.get("segment", "")
    preferred_channel = persona_dict.get("preferred_channel", "")
    purchase_history = persona_dict.get("purchase_history", [])

    data_confidence = round(min(99.0, 55.0 + (len(activity_logs) * 12.5)), 1)
    churn_risk = round(
        max(1.0, 100 - ((brand_attitude * 0.45) + (marketing_acceptance * 0.35) + (purchase_intent * 0.20))),
        1,
    )
    engagement_score = round((marketing_acceptance * 0.6) + (purchase_intent * 0.4), 1)
    return {
        **{k: v for k, v in persona_dict.items() if k not in ("profile", "purchase_history", "activity_logs", "cot")},
        "occupation_category": persona_dict.get("occupation_category") or _derive_occupation_category(occupation, age),
        "region": persona_dict.get("region") or _derive_region(age, segment),
        "household_type": persona_dict.get("household_type") or _derive_household_type(age, segment),
        "buy_channel": persona_dict.get("buy_channel") or _derive_buy_channel(preferred_channel),
        "product_group": persona_dict.get("product_group") or _derive_product_group(purchase_history),
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
        self.prompts = deepcopy(DEFAULT_PROMPTS)
        self.llm_parameters = deepcopy(DEFAULT_LLM_PARAMETERS)
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
    def list_personas(self, project_id: str | None = None) -> list[dict]:
        with SessionLocal() as session:
            query = session.query(PersonaModel)
            if project_id:
                query = query.filter_by(project_id=project_id)
            personas = query.all()
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
                    occupation_category=_derive_occupation_category(payload["occupation"], age),
                    region=_derive_region(age, payload["segment"]),
                    household_type=_derive_household_type(age, payload["segment"]),
                    segment=payload["segment"],
                    keywords=[payload["segment"], payload["occupation"], "AI"],
                    interests=["브랜드 탐색", "제품 비교", "온라인 리뷰"],
                    preferred_channel="YouTube",
                    buy_channel=_derive_buy_channel("YouTube"),
                    product_group=_derive_product_group(["Galaxy S24"]),
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

    def replace_personas(self, project_id: str, personas: list[dict], overwrite_existing: bool = True) -> list[dict]:
        created: list[dict] = []
        with SessionLocal() as session:
            existing_count = session.query(PersonaModel).filter_by(project_id=project_id).count()
            if existing_count and not overwrite_existing:
                raise ValueError("Personas already exist for this project.")

            if overwrite_existing:
                session.query(PersonaModel).filter_by(project_id=project_id).delete()

            for index, persona in enumerate(personas, start=1):
                age = _parse_age_range(str(persona.get("age_range", "")))
                name = persona.get("persona_name") or f"AI Persona {index}"
                description = persona.get("description", "")
                preferred_channel = persona.get("preferred_channel", "")
                purchase_history = _infer_purchase_history(persona)
                segment_tags = persona.get("segment_tags", [])
                region = next(
                    (
                        tag
                        for tag in segment_tags
                        if isinstance(tag, str) and tag not in {"SNS 숏폼", "영상 캠페인", "텍스트 브리핑"}
                    ),
                    _derive_region(age, name),
                )
                occupation = persona.get("persona_name_en") or f"{name} 사용자"
                model = PersonaModel(
                    id=f"prs-{uuid.uuid4().hex[:8]}",
                    project_id=project_id,
                    name=name,
                    age=age,
                    gender=persona.get("gender") or _infer_gender(description),
                    occupation=occupation,
                    occupation_category=_derive_occupation_category(occupation, age),
                    region=region,
                    household_type=_derive_household_type(age, name),
                    segment=name,
                    keywords=persona.get("keywords", []),
                    interests=persona.get("interests", []),
                    preferred_channel=preferred_channel,
                    buy_channel=_derive_buy_channel(preferred_channel),
                    product_group=_derive_product_group(purchase_history),
                    purchase_intent=float(persona.get("purchase_intent", 0.0)),
                    marketing_acceptance=float(persona.get("marketing_acceptance", 0.0)),
                    brand_attitude=float(persona.get("brand_attitude", 0.0)),
                    future_value=float(persona.get("future_value", 0.0)),
                    profile=description,
                    purchase_history=purchase_history,
                    individual_stories=persona.get("individual_stories", []),
                    activity_logs=persona.get("key_characteristics", []),
                    cot=[
                        "AI pipeline cluster stats analyzed",
                        "Persona profile generated",
                        "Backend normalized persona fields",
                    ],
                )
                session.add(model)
                created.append(_build_persona_response(model.to_dict()))

            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            if proj:
                proj.persona_count = len(created)
                proj.updated_at = _now()
            session.commit()
        return created

    def get_persona_detail(self, persona_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            p = session.query(PersonaModel).filter_by(id=persona_id).first()
            if p is None:
                return None
            d = p.to_dict()
            return {
                **_build_persona_response(d),
                "profile": d["profile"],
                "purchase_history": d["purchase_history"],
                "individual_stories": d.get("individual_stories", []),
                "activity_logs": d["activity_logs"],
                "cot": d["cot"],
            }

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
                        generation_source=question.get("generation_source", ""),
                        ai_rationale=question.get("ai_rationale", ""),
                        ai_evidence=question.get("ai_evidence", []),
                    )
                )
            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            if proj:
                proj.surveys_count = 1 if questions else 0
                proj.updated_at = _now()
            session.commit()
        return deepcopy(questions)

    # ── AI Jobs ───────────────────────────────────────────────────────────────
    def create_ai_job(self, project_id: str, job_type: str, payload: dict, created_by: str) -> dict:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        with SessionLocal() as session:
            job = AIJobModel(
                id=job_id,
                project_id=project_id,
                job_type=job_type,
                status="queued",
                progress=0,
                payload=payload,
                result_ref=None,
                error_code=None,
                error_message=None,
                created_by=created_by,
                created_at=_now(),
                started_at=None,
                completed_at=None,
            )
            session.add(job)
            session.commit()
            return job.to_dict()

    def get_ai_job(self, job_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            job = session.query(AIJobModel).filter_by(id=job_id).first()
            return job.to_dict() if job else None

    def list_ai_jobs(self, project_id: Optional[str] = None, job_type: Optional[str] = None) -> list[dict]:
        with SessionLocal() as session:
            query = session.query(AIJobModel)
            if project_id:
                query = query.filter_by(project_id=project_id)
            if job_type:
                query = query.filter_by(job_type=job_type)
            jobs = query.order_by(AIJobModel.created_at.desc()).all()
            return [job.to_dict() for job in jobs]

    def update_ai_job(self, job_id: str, **fields) -> Optional[dict]:
        with SessionLocal() as session:
            job = session.query(AIJobModel).filter_by(id=job_id).first()
            if job is None:
                return None
            for key, value in fields.items():
                setattr(job, key, value)
            session.commit()
            session.refresh(job)
            return job.to_dict()

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

    def get_response_distribution(self, project_id: str, question_id: str) -> list[dict]:
        with SessionLocal() as session:
            responses = (
                session.query(SimulationResponseModel)
                .filter_by(project_id=project_id, question_id=question_id)
                .all()
            )
            if not responses:
                return []
            counts: dict[str, int] = {}
            for r in responses:
                option = r.selected_option or ""
                counts[option] = counts.get(option, 0) + 1
            total = sum(counts.values())
            return [
                {"label": option, "value": round(count / total * 100, 1)}
                for option, count in counts.items()
            ]

    def get_response_keywords(self, project_id: str, limit: int = 9) -> list[dict]:
        import re
        STOPWORDS = {
            "이", "가", "은", "는", "을", "를", "에", "의", "과", "와", "도", "로", "으로",
            "에서", "합니다", "있습니다", "있다", "하는", "하고", "것", "더", "한", "이다",
            "들", "수", "그",
        }
        with SessionLocal() as session:
            responses = (
                session.query(SimulationResponseModel)
                .filter_by(project_id=project_id)
                .all()
            )
            if not responses:
                return []
            freq: dict[str, int] = {}
            for r in responses:
                texts = []
                if r.rationale:
                    texts.append(r.rationale)
                cot_list = r.cot or []
                for step in cot_list:
                    if isinstance(step, str):
                        texts.append(step)
                combined = " ".join(texts)
                words = re.findall(r"[가-힣]{2,}", combined)
                for word in words:
                    if word not in STOPWORDS:
                        freq[word] = freq.get(word, 0) + 1
            if not freq:
                return []
            sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]
            max_freq = sorted_words[0][1] if sorted_words else 1
            n = len(sorted_words)
            top_third = n // 3
            bottom_third = n - n // 3
            result = []
            for i, (word, count) in enumerate(sorted_words):
                normalized = round(count / max_freq * 100)
                if i < top_third:
                    trend = "up"
                elif i >= bottom_third:
                    trend = "down"
                else:
                    trend = "flat"
                result.append({"keyword": word, "frequency": normalized, "trend": trend})
            return result

    def get_setting(self, key: str, default=None):
        with SessionLocal() as session:
            setting = session.query(SettingModel).filter_by(key=key).first()
            if setting is None:
                return default
            return setting.value

    def set_setting(self, key: str, value) -> None:
        with SessionLocal() as session:
            setting = session.query(SettingModel).filter_by(key=key).first()
            if setting is None:
                setting = SettingModel(key=key, value=value, updated_at=_now())
                session.add(setting)
            else:
                setting.value = value
                setting.updated_at = _now()
            session.commit()

    def add_simulation_response(self, project_id: str, data: dict) -> dict:
        with SessionLocal() as session:
            response = SimulationResponseModel(
                id=data["id"],
                project_id=project_id,
                persona_name=data.get("persona_name", ""),
                segment=data.get("segment", ""),
                question_id=data.get("question_id", ""),
                question_text=data.get("question_text", ""),
                selected_option=data.get("selected_option", ""),
                rationale=data.get("rationale", ""),
                integrity_score=data.get("integrity_score", 0.0),
                timestamp=_now(),
                cot=data.get("cot", []),
            )
            session.add(response)

            sim = session.query(SimulationModel).filter_by(project_id=project_id).first()
            if sim:
                sim.completed_responses = (sim.completed_responses or 0) + 1
                if sim.target_responses and sim.target_responses > 0:
                    sim.progress = min(100, int(sim.completed_responses / sim.target_responses * 100))

            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            if proj:
                proj.response_count = (proj.response_count or 0) + 1
                proj.updated_at = _now()

            session.commit()
            return response.to_dict()

    def get_pending_simulation_pairs(self, project_id: str) -> list[tuple[dict, dict]]:
        with SessionLocal() as session:
            personas = session.query(PersonaModel).filter_by(project_id=project_id).all()
            questions = (
                session.query(SurveyQuestionModel)
                .filter_by(project_id=project_id)
                .order_by(SurveyQuestionModel.order)
                .all()
            )
            existing = (
                session.query(
                    SimulationResponseModel.persona_name,
                    SimulationResponseModel.question_id,
                )
                .filter_by(project_id=project_id)
                .all()
            )
            done_pairs = set((row[0], row[1]) for row in existing)
            pending = []
            for persona in personas:
                persona_dict = persona.to_dict()
                for question in questions:
                    question_dict = question.to_dict()
                    if (persona_dict["name"], question_dict["id"]) not in done_pairs:
                        pending.append((persona_dict, question_dict))
            return pending

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
            personas = session.query(PersonaModel).filter_by(project_id=project_id).all()
            responses = session.query(SimulationResponseModel).filter_by(project_id=project_id).all()
            simulation = session.query(SimulationModel).filter_by(project_id=project_id).first()

            persona_count = len(personas)
            response_count = len(responses)
            dominant_segment = "데이터 없음"
            if personas:
                segment_counts: dict[str, int] = {}
                for persona in personas:
                    segment = persona.segment or "미분류"
                    segment_counts[segment] = segment_counts.get(segment, 0) + 1
                dominant_segment = sorted(segment_counts.items(), key=lambda item: item[1], reverse=True)[0][0]

            top_question = None
            if responses:
                question_counts: dict[str, int] = {}
                for response in responses:
                    key = response.question_text or response.question_id
                    question_counts[key] = question_counts.get(key, 0) + 1
                top_question = sorted(question_counts.items(), key=lambda item: item[1], reverse=True)[0][0]

            response_progress = simulation.progress if simulation else (proj.progress if proj else 0)
            target_responses = proj.target_responses if proj else 0
            keyword_items = self.get_response_keywords(project_id, limit=5)
            questions = (
                session.query(SurveyQuestionModel)
                .filter_by(project_id=project_id)
                .order_by(SurveyQuestionModel.order)
                .all()
            )

            age_buckets = {"20대": 0, "30대": 0, "40대": 0, "50대+": 0}
            for persona in personas:
                if persona.age < 30:
                    age_buckets["20대"] += 1
                elif persona.age < 40:
                    age_buckets["30대"] += 1
                elif persona.age < 50:
                    age_buckets["40대"] += 1
                else:
                    age_buckets["50대+"] += 1
            highest_age_bucket = max(age_buckets.values(), default=1) or 1

            segment_cards = []
            if personas:
                segment_groups: dict[str, list[PersonaModel]] = {}
                for persona in personas:
                    segment_groups.setdefault(persona.segment or "미분류", []).append(persona)
                for segment_name, members in sorted(segment_groups.items(), key=lambda item: len(item[1]), reverse=True)[:3]:
                    channel_counts: dict[str, int] = {}
                    product_counts: dict[str, int] = {}
                    region_counts: dict[str, int] = {}
                    for member in members:
                        channel_counts[member.buy_channel or "데이터 없음"] = channel_counts.get(member.buy_channel or "데이터 없음", 0) + 1
                        product_counts[member.product_group or "데이터 없음"] = product_counts.get(member.product_group or "데이터 없음", 0) + 1
                        region_counts[member.region or "데이터 없음"] = region_counts.get(member.region or "데이터 없음", 0) + 1
                    segment_cards.append(
                        {
                            "segment": segment_name,
                            "count": len(members),
                            "share": round((len(members) / persona_count) * 100, 1) if persona_count else 0.0,
                            "buyChannel": sorted(channel_counts.items(), key=lambda item: item[1], reverse=True)[0][0],
                            "productGroup": sorted(product_counts.items(), key=lambda item: item[1], reverse=True)[0][0],
                            "region": sorted(region_counts.items(), key=lambda item: item[1], reverse=True)[0][0],
                        }
                    )

            keyword_chart_data = [
                {
                    "subject": item["keyword"],
                    "dominant": item["frequency"],
                    "baseline": 50,
                    "fullMark": 100,
                }
                for item in keyword_items
            ]

            question_strength_data = []
            detailed_distribution = []
            for question in questions[:7]:
                distribution = self.get_response_distribution(project_id, question.id)
                top_value = max((item["value"] for item in distribution), default=0)
                question_strength_data.append(
                    {
                        "label": question.id,
                        "value": top_value,
                    }
                )
                if distribution:
                    detailed_distribution.append(
                        {
                            "question_id": question.id,
                            "question_text": question.text,
                            "distribution": distribution,
                        }
                    )

            report = ReportModel(
                id=report_id,
                project_id=project_id,
                title=f"{project_name} 리포트",
                type="strategy",
                format="PDF",
                size="4.2MB",
                created_at=now,
                sections=[
                    {
                        "id": "summary",
                        "title": "종합 분석 요약",
                        "content": f"{project_name} 프로젝트는 현재 {persona_count}명의 페르소나와 {response_count}건의 시뮬레이션 응답을 기반으로 집계되었습니다.",
                    },
                    {
                        "id": "findings",
                        "title": "전략적 핵심 인사이트",
                        "content": f"가장 큰 세그먼트는 {dominant_segment}이며, 우선 검토 문항은 '{top_question or '집계 중'}' 입니다.",
                        "evidence": [
                            {"label": "최대 세그먼트", "value": dominant_segment},
                            {"label": "우선 문항", "value": top_question or "집계 중"},
                            {"label": "응답 진행률", "value": f"{response_progress}%"},
                        ],
                        "action": f"{dominant_segment} 세그먼트를 기준으로 메시지와 채널 전략을 우선 정렬합니다.",
                    },
                    {
                        "id": "detail",
                        "title": "데이터 기반 상세 분석",
                        "content": f"연령대별 분포와 문항별 우세 응답을 결합해 세그먼트별 기회 지점을 해석할 수 있습니다.",
                    },
                    {
                        "id": "segment",
                        "title": "세그먼트 기회 매트릭스",
                        "content": f"상위 세그먼트 {len(segment_cards)}개를 대상으로 구매 채널, 제품군, 지역 단위 액션을 정리했습니다.",
                    },
                ],
                kpis=[
                    {"label": "응답 진행률", "value": f"{response_progress}%"},
                    {"label": "목표 응답 수", "value": str(target_responses)},
                    {"label": "총 페르소나 수", "value": str(persona_count)},
                    {"label": "총 시뮬레이션 응답", "value": str(response_count)},
                ],
                charts=[
                    {"id": "keyword-radar", "type": "radar", "title": "상위 키워드 레이더", "data": keyword_chart_data},
                    {"id": "question-strength", "type": "area", "title": "문항별 우세 응답 강도", "data": question_strength_data},
                    {
                        "id": "age-distribution",
                        "type": "bar",
                        "title": "연령대별 분석 대상 규모",
                        "data": [
                            {"name": name, "value": value, "benchmark": highest_age_bucket}
                            for name, value in age_buckets.items()
                        ],
                    },
                    {
                        "id": "question-distribution",
                        "type": "distribution",
                        "title": top_question or "응답 분포",
                        "data": detailed_distribution,
                    },
                    {"id": "segment-cards", "type": "segment", "title": "세그먼트 기회 매트릭스", "data": segment_cards},
                ],
            )
            session.add(report)
            if proj:
                proj.reports_count = (proj.reports_count or 0) + 1
                proj.updated_at = now
            session.commit()
            return report.to_dict()

    def create_report_from_payload(self, project_id: str, payload: dict) -> dict:
        report_id = f"rpt-{uuid.uuid4().hex[:8]}"
        now = _now()
        with SessionLocal() as session:
            proj = session.query(ProjectModel).filter_by(id=project_id).first()
            report = ReportModel(
                id=report_id,
                project_id=project_id,
                title=payload.get("title") or f"{(proj.name if proj else project_id)} 리포트",
                type=payload.get("type", "strategy"),
                format=payload.get("format", "PDF"),
                size=payload.get("size", "4.2MB"),
                created_at=now,
                sections=payload.get("sections", []),
                kpis=payload.get("kpis", []),
                charts=payload.get("charts", []),
            )
            session.add(report)
            if proj:
                proj.reports_count = (proj.reports_count or 0) + 1
                proj.updated_at = now
            session.commit()
            return report.to_dict()


store = DbStore()
