from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.core.defaults import DEFAULT_LLM_PARAMETERS, DEFAULT_PROMPTS
from app.core.security import hash_password


class MockStore:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        admin_id = "usr-admin"
        project_id = f"prj-{uuid.uuid4().hex[:8]}"
        persona_id_1 = f"prs-{uuid.uuid4().hex[:8]}"
        persona_id_2 = f"prs-{uuid.uuid4().hex[:8]}"
        question_id_1 = f"q-{uuid.uuid4().hex[:8]}"
        question_id_2 = f"q-{uuid.uuid4().hex[:8]}"
        response_id_1 = f"rsp-{uuid.uuid4().hex[:8]}"
        response_id_2 = f"rsp-{uuid.uuid4().hex[:8]}"
        report_id = f"rpt-{uuid.uuid4().hex[:8]}"
        simulation_job_id = f"job-{uuid.uuid4().hex[:8]}"

        self.users = {
            admin_id: {
                "id": admin_id,
                "email": settings.DEFAULT_ADMIN_EMAIL,
                "hashed_password": hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                "name": settings.DEFAULT_ADMIN_NAME,
                "role": "admin",
                "is_active": True,
            }
        }
        self.revoked_refresh_tokens: set[str] = set()
        self.chat_sessions: dict[str, list[dict]] = {}
        self.prompts = deepcopy(DEFAULT_PROMPTS)
        self.llm_parameters = deepcopy(DEFAULT_LLM_PARAMETERS)

        self.projects = {
            project_id: {
                "id": project_id,
                "name": "Galaxy S26 컨셉 테스트",
                "type": "컨셉 테스트",
                "purpose": "AI 카메라 기능 반응 검증",
                "description": "신제품 컨셉 검증 프로젝트",
                "data_sources": ["customer_profile", "device", "bas_survey"],
                "tags": ["스마트폰", "신제품"],
                "status": "in_progress",
                "progress": 64,
                "response_count": 1182,
                "target_responses": 1847,
                "surveys_count": 1,
                "reports_count": 1,
                "persona_count": 6,
                "created_by": admin_id,
                "created_at": now - timedelta(days=4),
                "updated_at": now - timedelta(hours=2),
                "deleted_at": None,
            }
        }
        self.personas = {
            persona_id_1: {
                "id": persona_id_1,
                "project_id": project_id,
                "name": "김민준",
                "age": 29,
                "gender": "남성",
                "occupation": "게임 개발자",
                "occupation_category": "전문직",
                "region": "일본",
                "household_type": "1인 가구",
                "segment": "MZ 얼리어답터",
                "keywords": ["고성능", "AI카메라", "멀티태스킹"],
                "interests": ["모바일 게임", "영상 편집", "AI 자동화"],
                "preferred_channel": "YouTube",
                "buy_channel": "자급제",
                "product_group": "Galaxy S Ultra",
                "purchase_intent": 91.0,
                "marketing_acceptance": 84.0,
                "brand_attitude": 88.0,
                "future_value": 94.0,
                "profile": "최신 기술과 성능을 중시하는 20대 후반 게이머.",
                "purchase_history": ["S24 Ultra", "Tab S9 Ultra"],
                "activity_logs": ["게임 런처 실행", "카메라 비교 리뷰 시청"],
                "cot": ["고사양 기능 선호", "야간 촬영 중요", "AI 보정 체감 기대"],
            },
            persona_id_2: {
                "id": persona_id_2,
                "project_id": project_id,
                "name": "이서윤",
                "age": 37,
                "gender": "여성",
                "occupation": "마케터",
                "occupation_category": "직장인",
                "region": "대한민국",
                "household_type": "3인 이상",
                "segment": "실용 중시 가족형",
                "keywords": ["육아", "사진", "편의성"],
                "interests": ["가족 사진", "쇼핑", "여행"],
                "preferred_channel": "Instagram",
                "buy_channel": "공식몰",
                "product_group": "Galaxy S",
                "purchase_intent": 72.0,
                "marketing_acceptance": 79.0,
                "brand_attitude": 82.0,
                "future_value": 76.0,
                "profile": "실생활 편의와 사진 품질을 중요하게 보는 워킹맘.",
                "purchase_history": ["S23", "Galaxy Watch6"],
                "activity_logs": ["육아 유튜브 시청", "카메라 앱 사용"],
                "cot": ["생활 편의성 중요", "자동 보정 선호", "가성비 고려"],
            },
        }
        self.surveys = {
            project_id: [
                {
                    "id": question_id_1,
                    "text": "Galaxy S26 AI 카메라 컨셉에 대한 인지도는 어느 정도입니까?",
                    "type": "단일선택",
                    "options": ["매우 잘 안다", "어느 정도 안다", "들어봤다", "잘 모른다"],
                    "order": 1,
                    "status": "draft",
                },
                {
                    "id": question_id_2,
                    "text": "AI 카메라 컨셉이 구매 의향을 얼마나 높여준다고 느끼십니까?",
                    "type": "리커트척도",
                    "options": ["매우 크다", "크다", "보통", "낮다", "매우 낮다"],
                    "order": 2,
                    "status": "draft",
                },
            ]
        }
        self.simulations = {
            project_id: {
                "job_id": simulation_job_id,
                "status": "running",
                "progress": 64,
                "completed_responses": 1182,
                "target_responses": 1847,
            }
        }
        self.response_feed = {
            project_id: [
                {
                    "id": response_id_1,
                    "persona_name": "김민준",
                    "segment": "MZ 얼리어답터",
                    "question_id": question_id_2,
                    "question_text": "AI 카메라 컨셉이 구매 의향을 얼마나 높여준다고 느끼십니까?",
                    "selected_option": "매우 크다",
                    "rationale": "게임과 촬영을 동시에 만족시키는 업그레이드로 인식합니다.",
                    "integrity_score": 98.2,
                    "timestamp": now - timedelta(minutes=4),
                    "cot": ["스펙 민감도 높음", "카메라 성능 체감 기대", "업그레이드 의향 높음"],
                },
                {
                    "id": response_id_2,
                    "persona_name": "이서윤",
                    "segment": "실용 중시 가족형",
                    "question_id": question_id_1,
                    "question_text": "Galaxy S26 AI 카메라 컨셉에 대한 인지도는 어느 정도입니까?",
                    "selected_option": "어느 정도 안다",
                    "rationale": "광고에서 생활 사진 개선 메시지를 보고 관심을 가졌습니다.",
                    "integrity_score": 94.7,
                    "timestamp": now - timedelta(minutes=7),
                    "cot": ["광고 노출", "가족 사진 중심", "편의성 기대"],
                },
            ]
        }
        self.reports = {
            report_id: {
                "id": report_id,
                "project_id": project_id,
                "title": "Galaxy S26 컨셉 테스트 리포트",
                "type": "strategy",
                "format": "PDF",
                "size": "4.8MB",
                "created_at": now - timedelta(hours=1),
                "sections": [
                    {"id": "summary", "title": "개요", "content": "핵심 타겟은 30대 테크 게이머입니다."},
                    {"id": "insight", "title": "인사이트", "content": "AI 카메라 효용이 구매 전환에 크게 기여합니다."},
                ],
                "kpis": [
                    {"label": "구매 의향", "value": "68.7%"},
                    {"label": "응답 정합성", "value": "98.4%"},
                ],
                "charts": [
                    {"id": "chart-01", "type": "bar", "title": "문항별 응답 분포"},
                ],
            }
        }

    def get_user(self, user_id: str) -> Optional[dict]:
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[dict]:
        return next((user for user in self.users.values() if user["email"] == email), None)

    def list_projects(self) -> list[dict]:
        return [deepcopy(project) for project in self.projects.values() if project["deleted_at"] is None]

    def create_project(self, payload: dict, user_id: str) -> dict:
        project_id = f"prj-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        project = {
            "id": project_id,
            "name": payload["name"],
            "type": payload["type"],
            "purpose": payload["purpose"],
            "description": payload.get("description"),
            "data_sources": payload.get("data_sources", []),
            "tags": payload.get("tags", []),
            "status": "draft",
            "progress": 0,
            "response_count": 0,
            "target_responses": payload["target_responses"],
            "surveys_count": 0,
            "reports_count": 0,
            "persona_count": 0,
            "created_by": user_id,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
        self.projects[project_id] = project
        self.surveys[project_id] = []
        self.response_feed[project_id] = []
        return deepcopy(project)

    def update_project(self, project_id: str, payload: dict) -> Optional[dict]:
        project = self.projects.get(project_id)
        if project is None or project["deleted_at"] is not None:
            return None
        for key in ("name", "description", "tags"):
            if key in payload and payload[key] is not None:
                project[key] = payload[key]
        project["updated_at"] = datetime.now(timezone.utc)
        return deepcopy(project)

    def soft_delete_project(self, project_id: str) -> bool:
        project = self.projects.get(project_id)
        if project is None or project["deleted_at"] is not None:
            return False
        project["deleted_at"] = datetime.now(timezone.utc)
        return True

    def list_personas(self, project_id: str) -> list[dict]:
        return [self._build_persona_response(item) for item in self.personas.values() if item["project_id"] == project_id]

    def create_persona_pool(self, payload: dict) -> list[dict]:
        created: list[dict] = []
        for index in range(payload["size"]):
            persona_id = f"prs-{uuid.uuid4().hex[:8]}"
            age = 25 + (index % 15)
            purchase_intent = float(60 + (index % 30))
            marketing_acceptance = float(55 + (index % 35))
            brand_attitude = float(58 + (index % 28))
            future_value = round((purchase_intent * 0.45) + (marketing_acceptance * 0.35) + (brand_attitude * 0.2), 1)
            self.personas[persona_id] = {
                "id": persona_id,
                "project_id": payload["project_id"],
                "name": f"{payload['segment']} Persona {index + 1}",
                "age": age,
                "gender": payload["gender"],
                "occupation": payload["occupation"],
                "occupation_category": "직장인",
                "region": "대한민국",
                "household_type": "1인 가구",
                "segment": payload["segment"],
                "keywords": [payload["segment"], payload["occupation"], "AI"],
                "interests": ["브랜드 탐색", "제품 비교", "온라인 리뷰"],
                "preferred_channel": "YouTube",
                "buy_channel": "자급제",
                "product_group": "Galaxy S",
                "purchase_intent": purchase_intent,
                "marketing_acceptance": marketing_acceptance,
                "brand_attitude": brand_attitude,
                "future_value": future_value,
                "profile": f"{payload['segment']} 조건을 기반으로 생성된 디지털 트윈 페르소나",
                "purchase_history": ["Galaxy S24"],
                "activity_logs": ["세그먼트 기반 생성"],
                "cot": ["세그먼트 조건 적용", "기본 점수 생성", "채널 선호 계산"],
            }
            created.append(self._build_persona_response(self.personas[persona_id]))
        if payload["project_id"] in self.projects:
            self.projects[payload["project_id"]]["persona_count"] += len(created)
            self.projects[payload["project_id"]]["updated_at"] = datetime.now(timezone.utc)
        return created

    def get_persona_detail(self, persona_id: str) -> Optional[dict]:
        persona = self.personas.get(persona_id)
        if persona is None:
            return None
        return deepcopy({**self._build_persona_response(persona), "profile": persona["profile"], "purchase_history": persona["purchase_history"], "activity_logs": persona["activity_logs"], "cot": persona["cot"]})

    def list_survey_questions(self, project_id: str) -> list[dict]:
        return deepcopy(self.surveys.get(project_id, []))

    def replace_survey_questions(self, project_id: str, questions: list[dict]) -> list[dict]:
        for index, question in enumerate(questions, start=1):
            question["order"] = index
        self.surveys[project_id] = questions
        if project_id in self.projects:
            self.projects[project_id]["surveys_count"] = 1 if questions else 0
            self.projects[project_id]["updated_at"] = datetime.now(timezone.utc)
        return deepcopy(questions)

    def create_report(self, project_id: str) -> dict:
        report_id = f"rpt-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        personas = [persona for persona in self.personas.values() if persona["project_id"] == project_id]
        responses = self.response_feed.get(project_id, [])
        simulation = self.simulations.get(project_id)
        dominant_segment = "데이터 없음"
        if personas:
            segment_counts: dict[str, int] = {}
            for persona in personas:
                segment = persona["segment"]
                segment_counts[segment] = segment_counts.get(segment, 0) + 1
            dominant_segment = sorted(segment_counts.items(), key=lambda item: item[1], reverse=True)[0][0]
        top_question = responses[0]["question_text"] if responses else "집계 중"
        report = {
            "id": report_id,
            "project_id": project_id,
            "title": f"{self.projects[project_id]['name']} 리포트",
            "type": "strategy",
            "format": "PDF",
            "size": "4.2MB",
            "created_at": now,
            "sections": [
                {
                    "id": "overview",
                    "title": "개요",
                    "content": f"{self.projects[project_id]['name']} 프로젝트는 {len(personas)}명의 페르소나와 {len(responses)}건의 응답을 기반으로 집계되었습니다.",
                },
                {
                    "id": "recommendation",
                    "title": "권장사항",
                    "content": f"가장 큰 세그먼트는 {dominant_segment}이며, 우선 검토 문항은 '{top_question}' 입니다.",
                },
            ],
            "kpis": [
                {"label": "응답 진행률", "value": f"{simulation['progress'] if simulation else 0}%"},
                {"label": "목표 응답 수", "value": str(self.projects[project_id]["target_responses"])},
            ],
            "charts": [{"id": "chart-01", "type": "bar", "title": top_question}],
        }
        self.reports[report_id] = report
        self.projects[project_id]["reports_count"] += 1
        self.projects[project_id]["updated_at"] = now
        return deepcopy(report)

    def _build_persona_response(self, persona: dict) -> dict:
        data_confidence = round(min(99.0, 55.0 + (len(persona["activity_logs"]) * 12.5)), 1)
        churn_risk = round(max(1.0, 100 - ((persona["brand_attitude"] * 0.45) + (persona["marketing_acceptance"] * 0.35) + (persona["purchase_intent"] * 0.20))), 1)
        engagement_score = round((persona["marketing_acceptance"] * 0.6) + (persona["purchase_intent"] * 0.4), 1)
        return {
            "id": persona["id"],
            "project_id": persona["project_id"],
            "name": persona["name"],
            "age": persona["age"],
            "gender": persona["gender"],
            "occupation": persona["occupation"],
            "occupation_category": persona["occupation_category"],
            "region": persona["region"],
            "household_type": persona["household_type"],
            "segment": persona["segment"],
            "keywords": persona["keywords"],
            "interests": persona["interests"],
            "preferred_channel": persona["preferred_channel"],
            "buy_channel": persona["buy_channel"],
            "product_group": persona["product_group"],
            "purchase_intent": persona["purchase_intent"],
            "marketing_acceptance": persona["marketing_acceptance"],
            "brand_attitude": persona["brand_attitude"],
            "churn_risk": churn_risk,
            "score": {
                "churn_risk": churn_risk,
                "engagement_score": engagement_score,
                "future_value": persona["future_value"],
                "data_confidence": data_confidence,
            },
        }


store = MockStore()
