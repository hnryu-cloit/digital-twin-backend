"""
UI에 표시되는 데이터와 일치하는 실제 시드 데이터를 SQLite DB에 저장합니다.
실행: python scripts/seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone

from app.services.db_store import SessionLocal, engine, init_db
from app.services.db_models import (
    ProjectModel,
    PersonaModel,
    SurveyQuestionModel,
    SimulationModel,
    SimulationResponseModel,
    ReportModel,
)

now = datetime.now(timezone.utc)


def seed():
    init_db()

    with SessionLocal() as session:
        # 기존 시드 데이터 중복 방지
        if session.query(ProjectModel).filter_by(id="prj-001").first():
            print("이미 시드 데이터가 존재합니다. 건너뜁니다.")
            return

        # ── 프로젝트 4개 ──────────────────────────────────────────────────────
        projects = [
            ProjectModel(
                id="prj-001",
                name="Galaxy S26 컨셉 테스트",
                type="컨셉 테스트",
                purpose="AI 카메라 기능 반응 검증",
                description="신제품 컨셉 검증 프로젝트. MZ세대 테크 얼리어답터를 중심으로 AI 카메라 기능의 구매 전환 효과를 측정합니다.",
                data_sources=["customer_profile", "device", "bas_survey"],
                tags=["스마트폰", "신제품"],
                status="진행중",
                progress=67,
                response_count=1340,
                target_responses=2000,
                surveys_count=1,
                reports_count=1,
                persona_count=6,
                created_by="usr-admin",
                created_at=now - timedelta(days=4),
                updated_at=now - timedelta(hours=2),
                deleted_at=None,
            ),
            ProjectModel(
                id="prj-002",
                name="MZ세대 스마트폰 Usage 조사",
                type="Usage 조사",
                purpose="MZ세대 스마트폰 사용 행태 심층 분석",
                description="20-30대 MZ세대의 스마트폰 사용 패턴, 앱 이용 행태, 카메라 활용도를 분석합니다.",
                data_sources=["customer_profile", "usage_log"],
                tags=["MZ", "사용행태"],
                status="분석중",
                progress=100,
                response_count=3200,
                target_responses=3000,
                surveys_count=1,
                reports_count=2,
                persona_count=8,
                created_by="usr-admin",
                created_at=now - timedelta(days=12),
                updated_at=now - timedelta(days=1),
                deleted_at=None,
            ),
            ProjectModel(
                id="prj-003",
                name="브랜드 인지도 조사 Q1 2026",
                type="브랜드 인식",
                purpose="삼성 갤럭시 브랜드 인지도 및 경쟁 포지셔닝 분석",
                description="2026년 1분기 삼성 갤럭시 브랜드 인지도, 선호도, 경쟁사 대비 포지셔닝을 측정합니다.",
                data_sources=["customer_profile", "brand_survey"],
                tags=["브랜드", "분기"],
                status="완료",
                progress=100,
                response_count=5000,
                target_responses=5000,
                surveys_count=2,
                reports_count=3,
                persona_count=10,
                created_by="usr-admin",
                created_at=now - timedelta(days=30),
                updated_at=now - timedelta(days=3),
                deleted_at=None,
            ),
            ProjectModel(
                id="prj-004",
                name="신규 UI 사용성 테스트 v2",
                type="UX 테스트",
                purpose="갤럭시 원UI 6.0 신규 인터페이스 사용성 검증",
                description="원UI 6.0 업데이트 이후 새로운 인터페이스에 대한 사용자 경험 및 만족도를 측정합니다.",
                data_sources=["ux_survey"],
                tags=["UI", "사용성"],
                status="초안",
                progress=0,
                response_count=0,
                target_responses=500,
                surveys_count=0,
                reports_count=0,
                persona_count=0,
                created_by="usr-admin",
                created_at=now - timedelta(days=5),
                updated_at=now - timedelta(days=5),
                deleted_at=None,
            ),
        ]
        session.add_all(projects)

        # ── 페르소나 6개 (prj-001) ────────────────────────────────────────────
        personas = [
            PersonaModel(
                id="prs-001",
                project_id="prj-001",
                name="김민준",
                age=29,
                gender="남성",
                occupation="게임 개발자",
                segment="MZ 얼리어답터",
                keywords=["고성능", "AI카메라", "멀티태스킹"],
                interests=["모바일 게임", "영상 편집", "AI 자동화"],
                preferred_channel="YouTube",
                purchase_intent=91.0,
                marketing_acceptance=84.0,
                brand_attitude=88.0,
                future_value=94.0,
                profile="최신 기술과 성능을 중시하는 20대 후반 게이머. Galaxy S 시리즈를 꾸준히 구매해온 충성 고객으로, AI 카메라 기능에 큰 기대를 품고 있습니다.",
                purchase_history=["S24 Ultra", "Tab S9 Ultra"],
                activity_logs=["게임 런처 실행", "카메라 비교 리뷰 시청", "S26 스펙 검색"],
                cot=["고사양 기능 선호", "야간 촬영 중요", "AI 보정 체감 기대"],
            ),
            PersonaModel(
                id="prs-002",
                project_id="prj-001",
                name="이서윤",
                age=37,
                gender="여성",
                occupation="마케터",
                segment="실용 중시 가족형",
                keywords=["육아", "사진", "편의성"],
                interests=["가족 사진", "쇼핑", "여행"],
                preferred_channel="Instagram",
                purchase_intent=72.0,
                marketing_acceptance=79.0,
                brand_attitude=82.0,
                future_value=76.0,
                profile="실생활 편의와 사진 품질을 중요하게 보는 워킹맘. 아이 사진을 자주 찍고 SNS에 공유하며, 자동 보정 기능에 특히 관심이 많습니다.",
                purchase_history=["S23", "Galaxy Watch6"],
                activity_logs=["육아 유튜브 시청", "카메라 앱 사용", "가족 사진 공유"],
                cot=["생활 편의성 중요", "자동 보정 선호", "가성비 고려"],
            ),
            PersonaModel(
                id="prs-003",
                project_id="prj-001",
                name="박지훈",
                age=24,
                gender="남성",
                occupation="대학원생",
                segment="MZ 얼리어답터",
                keywords=["가성비", "최신폰", "유튜브"],
                interests=["유튜브 콘텐츠", "게임", "테크 리뷰"],
                preferred_channel="YouTube",
                purchase_intent=85.0,
                marketing_acceptance=91.0,
                brand_attitude=79.0,
                future_value=82.0,
                profile="최신 스마트폰 트렌드를 팔로우하는 20대 초반 얼리어답터. 유튜브 테크 채널을 즐겨보며 새로운 AI 기능에 빠르게 반응합니다.",
                purchase_history=["S23 FE"],
                activity_logs=["테크 리뷰 영상 시청", "S26 사전 예약 페이지 방문", "AI 기능 비교"],
                cot=["신기술에 빠른 반응", "SNS 인플루언서 영향", "가격 민감도 중간"],
            ),
            PersonaModel(
                id="prs-004",
                project_id="prj-001",
                name="최민지",
                age=32,
                gender="여성",
                occupation="프리랜서 디자이너",
                segment="프리미엄 소비자",
                keywords=["디자인", "카메라 화질", "프리미엄"],
                interests=["사진 촬영", "포트폴리오", "아트"],
                preferred_channel="Instagram",
                purchase_intent=78.0,
                marketing_acceptance=67.0,
                brand_attitude=85.0,
                future_value=80.0,
                profile="카메라 화질과 디자인을 최우선으로 여기는 프리랜서 디자이너. 전문 사진 작업에 스마트폰을 보조로 활용하며 화질 개선에 민감합니다.",
                purchase_history=["S22 Ultra", "Galaxy Buds2 Pro"],
                activity_logs=["카메라 샘플 사진 비교", "Pro 모드 사용", "포트폴리오 촬영"],
                cot=["카메라 스펙 최우선", "프리미엄 모델 선호", "AI 보정보다 원본 화질 중시"],
            ),
            PersonaModel(
                id="prs-005",
                project_id="prj-001",
                name="강현우",
                age=45,
                gender="남성",
                occupation="IT 기업 임원",
                segment="비즈니스 프로",
                keywords=["업무 효율", "보안", "프리미엄"],
                interests=["비즈니스 앱", "보안", "생산성"],
                preferred_channel="LinkedIn",
                purchase_intent=65.0,
                marketing_acceptance=55.0,
                brand_attitude=90.0,
                future_value=88.0,
                profile="업무 효율과 보안을 중시하는 IT 기업 임원. 삼성 Knox를 신뢰하며 기업용 기능을 최우선으로 고려합니다.",
                purchase_history=["S24 Ultra", "Z Fold5", "Galaxy Book Pro"],
                activity_logs=["비즈니스 앱 사용", "Knox 보안 설정", "회의 영상 촬영"],
                cot=["보안 기능 최우선", "생산성 앱 연동 중요", "AI 기능보다 안정성 선호"],
            ),
            PersonaModel(
                id="prs-006",
                project_id="prj-001",
                name="정수아",
                age=28,
                gender="여성",
                occupation="뷰티 크리에이터",
                segment="콘텐츠 크리에이터",
                keywords=["셀피", "영상미", "트렌드"],
                interests=["뷰티", "콘텐츠 제작", "SNS"],
                preferred_channel="TikTok",
                purchase_intent=88.0,
                marketing_acceptance=95.0,
                brand_attitude=76.0,
                future_value=85.0,
                profile="SNS 콘텐츠 제작에 특화된 뷰티 크리에이터. 셀피 화질과 영상 안정화 기능을 매우 중요하게 여기며 AI 보정 기능에 매우 호의적입니다.",
                purchase_history=["S23"],
                activity_logs=["셀피 촬영", "숏폼 영상 제작", "AI 필터 사용"],
                cot=["셀피 화질 최우선", "AI 보정 매우 선호", "트렌드 민감도 최고"],
            ),
        ]
        session.add_all(personas)

        # ── 설문 문항 12개 (prj-001) ──────────────────────────────────────────
        questions = [
            SurveyQuestionModel(
                id="q-001",
                project_id="prj-001",
                text="귀하는 현재 어떤 스마트폰을 사용하고 계십니까?",
                type="단일선택",
                options=["Galaxy S 시리즈", "Galaxy A 시리즈", "iPhone", "기타 안드로이드", "기타"],
                order=1,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-002",
                project_id="prj-001",
                text="Galaxy S26 AI 카메라 컨셉에 대해 얼마나 알고 계십니까?",
                type="단일선택",
                options=["매우 잘 안다", "어느 정도 안다", "들어봤다", "잘 모른다"],
                order=2,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-003",
                project_id="prj-001",
                text="AI 카메라 기능 중 가장 매력적으로 느끼는 기능을 모두 선택해 주세요.",
                type="복수선택",
                options=["야간 촬영 자동 보정", "AI 인물 사진 보정", "실시간 장면 분석", "AI 줌 선명도 향상", "자동 편집 및 하이라이트"],
                order=3,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-004",
                project_id="prj-001",
                text="AI 카메라 컨셉이 구매 의향을 얼마나 높여준다고 느끼십니까?",
                type="리커트척도",
                options=["매우 크다", "크다", "보통", "낮다", "매우 낮다"],
                order=4,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-005",
                project_id="prj-001",
                text="현재 스마트폰 카메라 사용 시 가장 불편한 점은 무엇입니까?",
                type="복수선택",
                options=["야간 촬영 품질", "흔들림 보정", "줌 화질 저하", "편집 번거로움", "파일 용량 과다"],
                order=5,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-006",
                project_id="prj-001",
                text="AI 카메라 기능을 위해 추가로 지불할 의향이 있는 금액은 얼마입니까?",
                type="단일선택",
                options=["없다", "1~5만원", "5~10만원", "10~20만원", "20만원 이상"],
                order=6,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-007",
                project_id="prj-001",
                text="Galaxy S26 AI 카메라에 대한 전반적인 인상을 어떻게 평가하십니까?",
                type="리커트척도",
                options=["매우 혁신적", "혁신적", "보통", "기존과 비슷", "기존보다 못함"],
                order=7,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-008",
                project_id="prj-001",
                text="AI 카메라 기능을 주로 어떤 상황에서 활용할 것 같습니까? (복수 선택)",
                type="복수선택",
                options=["일상 스냅 촬영", "여행 및 아웃도어", "음식 사진", "인물/셀피", "비즈니스/문서 촬영"],
                order=8,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-009",
                project_id="prj-001",
                text="Galaxy S26 출시 시 구매 계획이 있으십니까?",
                type="단일선택",
                options=["출시일에 바로 구매", "출시 후 1~3개월 내 구매", "리뷰 확인 후 구매 결정", "현재는 구매 계획 없음"],
                order=9,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-010",
                project_id="prj-001",
                text="Galaxy S26 AI 카메라의 가장 강력한 경쟁 우위는 무엇이라고 생각하십니까?",
                type="단일선택",
                options=["AI 야간 촬영", "실시간 피사체 인식", "AI 영상 편집", "경쟁사 대비 처리 속도", "Galaxy AI 생태계 연동"],
                order=10,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-011",
                project_id="prj-001",
                text="Galaxy S26을 주변에 추천할 의향은 어느 정도입니까? (NPS 기준 0~10점)",
                type="리커트척도",
                options=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
                order=11,
                status="confirmed",
            ),
            SurveyQuestionModel(
                id="q-012",
                project_id="prj-001",
                text="Galaxy S26 AI 카메라 기능에 대한 전반적인 인상을 자유롭게 적어주세요.",
                type="주관식",
                options=[],
                order=12,
                status="confirmed",
            ),
        ]
        session.add_all(questions)

        # ── 시뮬레이션 상태 (prj-001) ─────────────────────────────────────────
        simulation = SimulationModel(
            project_id="prj-001",
            job_id="job-001",
            status="running",
            progress=67,
            completed_responses=1340,
            target_responses=2000,
        )
        session.add(simulation)

        # ── 시뮬레이션 응답 피드 (prj-001) ───────────────────────────────────
        responses = [
            SimulationResponseModel(
                id="rsp-001",
                project_id="prj-001",
                persona_name="김민준",
                segment="MZ 얼리어답터",
                question_id="q-004",
                question_text="AI 카메라 컨셉이 구매 의향을 얼마나 높여준다고 느끼십니까?",
                selected_option="매우 크다",
                rationale="게임과 촬영을 동시에 만족시키는 업그레이드로 인식합니다. AI 야간 촬영이 특히 기대됩니다.",
                integrity_score=98.2,
                timestamp=now - timedelta(minutes=4),
                cot=["스펙 민감도 높음", "카메라 성능 체감 기대", "업그레이드 의향 높음"],
            ),
            SimulationResponseModel(
                id="rsp-002",
                project_id="prj-001",
                persona_name="이서윤",
                segment="실용 중시 가족형",
                question_id="q-002",
                question_text="Galaxy S26 AI 카메라 컨셉에 대해 얼마나 알고 계십니까?",
                selected_option="어느 정도 안다",
                rationale="광고에서 생활 사진 개선 메시지를 보고 관심을 가졌습니다. 아이 사진 자동 보정이 매우 유용할 것 같습니다.",
                integrity_score=94.7,
                timestamp=now - timedelta(minutes=7),
                cot=["광고 노출", "가족 사진 중심", "편의성 기대"],
            ),
            SimulationResponseModel(
                id="rsp-003",
                project_id="prj-001",
                persona_name="박지훈",
                segment="MZ 얼리어답터",
                question_id="q-003",
                question_text="AI 카메라 기능 중 가장 매력적으로 느끼는 기능을 모두 선택해 주세요.",
                selected_option="야간 촬영 자동 보정, AI 줌 선명도 향상",
                rationale="유튜브 리뷰에서 야간 촬영 성능이 압도적이라는 평가를 확인했습니다.",
                integrity_score=91.8,
                timestamp=now - timedelta(minutes=11),
                cot=["테크 리뷰 영향", "성능 비교 중시", "빠른 의사결정"],
            ),
            SimulationResponseModel(
                id="rsp-004",
                project_id="prj-001",
                persona_name="최민지",
                segment="프리미엄 소비자",
                question_id="q-007",
                question_text="Galaxy S26 AI 카메라에 대한 전반적인 인상을 어떻게 평가하십니까?",
                selected_option="혁신적",
                rationale="디자이너 관점에서 AI 보정 퀄리티가 실제로 향상되었다고 느낍니다. 단, 원본 보존 옵션이 필요합니다.",
                integrity_score=96.4,
                timestamp=now - timedelta(minutes=14),
                cot=["화질 전문성 보유", "AI 보정 효과 인정", "원본 파일 중시"],
            ),
            SimulationResponseModel(
                id="rsp-005",
                project_id="prj-001",
                persona_name="강현우",
                segment="비즈니스 프로",
                question_id="q-009",
                question_text="Galaxy S26 출시 시 구매 계획이 있으십니까?",
                selected_option="출시 후 1~3개월 내 구매",
                rationale="기업 IT 정책상 즉시 구매보다 안정성 검증 후 구매를 선호합니다. S26의 보안 업데이트 내역 확인 필요합니다.",
                integrity_score=99.1,
                timestamp=now - timedelta(minutes=18),
                cot=["기업 IT 정책 준수", "안정성 검증 우선", "보안 기능 최우선"],
            ),
            SimulationResponseModel(
                id="rsp-006",
                project_id="prj-001",
                persona_name="정수아",
                segment="콘텐츠 크리에이터",
                question_id="q-003",
                question_text="AI 카메라 기능 중 가장 매력적으로 느끼는 기능을 모두 선택해 주세요.",
                selected_option="AI 인물 사진 보정, 자동 편집 및 하이라이트",
                rationale="크리에이터로서 셀피 AI 보정과 자동 편집은 콘텐츠 제작 시간을 획기적으로 줄여줄 것 같습니다.",
                integrity_score=97.3,
                timestamp=now - timedelta(minutes=22),
                cot=["콘텐츠 제작 효율 중시", "AI 보정 매우 선호", "트렌드 선도 의식"],
            ),
        ]
        session.add_all(responses)

        # ── 리포트 (prj-001) ─────────────────────────────────────────────────
        report = ReportModel(
            id="rpt-001",
            project_id="prj-001",
            title="Galaxy S26 컨셉 테스트 전략 리포트",
            type="strategy",
            format="PDF",
            size="4.8MB",
            created_at=now - timedelta(hours=1),
            sections=[
                {
                    "id": "summary",
                    "title": "개요",
                    "content": "Galaxy S26 AI 카메라 컨셉 테스트 결과, 핵심 타겟은 30대 테크 게이머로 확인되었습니다. 전체 응답자의 68.7%가 구매 의향을 표시했으며, AI 야간 촬영 기능이 핵심 전환 동인으로 작용했습니다."
                },
                {
                    "id": "insight",
                    "title": "핵심 인사이트",
                    "content": "AI 카메라 효용이 구매 전환에 크게 기여합니다. MZ 얼리어답터 세그먼트에서 구매 의향이 +23.4% 상승했으며, 야간 촬영 자동 보정이 가장 높은 관심을 받았습니다."
                },
                {
                    "id": "segment",
                    "title": "세그먼트 분석",
                    "content": "MZ 얼리어답터(35%)와 콘텐츠 크리에이터(22%)가 높은 구매 의향을 보인 반면, 비즈니스 프로(18%)는 안정성 검증 후 구매를 선호합니다."
                },
                {
                    "id": "recommendation",
                    "title": "전략 권장사항",
                    "content": "핵심 타겟인 MZ 얼리어답터를 대상으로 야간 촬영 AI 보정 기능을 전면에 내세운 YouTube 마케팅을 강화하고, 크리에이터 인플루언서를 활용한 바이럴 캠페인을 병행하는 것을 권장합니다."
                },
            ],
            kpis=[
                {"label": "샘플 규모", "value": "30,000"},
                {"label": "구매 의향", "value": "68.7%"},
                {"label": "응답 정합성", "value": "98.4%"},
                {"label": "전략 액션", "value": "03"},
            ],
            charts=[
                {"id": "chart-01", "type": "bar", "title": "문항별 응답 분포"},
                {"id": "chart-02", "type": "radar", "title": "세그먼트별 평가 차원"},
                {"id": "chart-03", "type": "area", "title": "구매 의향 트렌드 (7주)"},
            ],
        )
        session.add(report)

        session.commit()
        print("✅ 시드 데이터 저장 완료!")
        print("  - 프로젝트 4개")
        print("  - 페르소나 6개 (prj-001)")
        print("  - 설문 문항 12개 (prj-001)")
        print("  - 시뮬레이션 응답 6개 (prj-001)")
        print("  - 리포트 1개 (prj-001)")


if __name__ == "__main__":
    seed()