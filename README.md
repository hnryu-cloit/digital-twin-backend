# digital-twin-backend

> **⚠️ 전역 시스템 제약조건 및 코드 컨벤션**
> 본 프로젝트는 엔터프라이즈 B2B SaaS 아키텍처를 지향하며, 엄격한 코드 컨벤션을 따릅니다.
> 자세한 사항은 루트 디렉토리의 [`docs/conventions.md`](../docs/conventions.md)를 반드시 확인하세요.
> 주요 백엔드 제약: **Layered Architecture (Router-Service-Repo), FastAPI + Pydantic v2, Ruff & Mypy Strict**

Samsung Digital Customer Twin FastAPI backend

## Stack

- **Python 3.9+** / FastAPI / Uvicorn
- **SQLite** (`aiosqlite` + SQLAlchemy 2.0 sync engine) — 파일 기반 영속 DB
- **Alembic** — 향후 PostgreSQL 마이그레이션 대비
- **Gemini API** (`google-generativeai 0.8.3`) — 챗 어시스턴트·설문 생성·시뮬레이션 인사이트 AI 연동

## Structure

```
app/
├── api/v1/endpoints/   # API routers (auth/projects/personas/surveys/simulations/reports/...)
├── core/               # config, dependencies, security
├── models/             # SQLAlchemy ORM models (PostgreSQL 대비용)
├── schemas/            # Pydantic v2 schemas
├── services/
│   ├── db_models.py    # SQLite 영속 ORM 모델 (9개 테이블, settings 포함)
│   ├── db_store.py     # SQLite 기반 DbStore — 집계·설정 영속화 메서드 포함
│   ├── gemini_client.py  # Gemini API 래퍼 (키 미설정 시 None 반환 graceful fallback)
│   └── simulation_runner.py  # BackgroundTasks용 배치 시뮬레이션 응답 생성기
└── main.py             # FastAPI 엔트리포인트 (startup: init_db)

scripts/
└── seed_data.py        # 초기 시드 데이터 (프로젝트 4 · 페르소나 6 · 설문 12 · 리포트 1)
```

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# .env 설정
# DATABASE_URL=sqlite+aiosqlite:///./digital_twin.db
# GEMINI_API_KEY=<your-key>   # 없으면 AI 기능 폴백 동작
uvicorn app.main:app --reload
```

> 앱 시작 시 `init_db()`가 자동으로 테이블을 생성하고 admin 계정을 시딩합니다.

### 시드 데이터 초기 투입

```bash
python scripts/seed_data.py
```

이미 데이터가 존재하면 건너뜁니다(idempotent).

Docs: `http://localhost:8000/docs`

## API Shape

- Base prefix: `/api`
- Auth: `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`
- Projects: `/api/projects`
- Personas: `/api/personas`, `/api/personas/pool`
- Segments: `/api/segments/aggregate`, `/api/segments/chart`, `/api/segments/kpi`
- Surveys: `/api/surveys/generate`, `/api/surveys/{project_id}/questions`, `/api/surveys/confirm`
- Simulations: `/api/simulations/control`, `/api/simulations/progress`, `/api/simulations/feed`, `/api/simulations/distribution`, `/api/simulations/keywords`, `/api/simulations/cot/{id}`
- Reports: `/api/reports`, `/api/reports/generate`, `/api/reports/{id}/download`
- Assistant: `/api/assistant/chat`
- Settings: `/api/settings/prompts`, `/api/settings/llm-parameters`

## DB 모델 (SQLite 테이블)

| 테이블 | 설명 |
|--------|------|
| `users` | 사용자 계정 (id · email · hashed_password · role) |
| `projects` | 리서치 프로젝트 (status · progress · response_count 등) |
| `personas` | 디지털 트윈 페르소나 (점수 4종 · 관심사 · CoT) |
| `survey_questions` | 설문 문항 (type · options · order · status) |
| `simulations` | 시뮬레이션 진행 상태 (job_id · progress · completed_responses) |
| `simulation_responses` | 페르소나별 응답 피드 (integrity_score · CoT) |
| `reports` | 생성 리포트 (sections · kpis · charts JSON) |
| `revoked_tokens` | 로그아웃 토큰 블랙리스트 |
| `settings` | 프롬프트·LLM 파라미터 등 운영 설정 DB 영속화 (key/value JSON) |

## AI 기능 (Gemini)

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 어시스턴트 챗 | `POST /api/assistant/chat` | 대화 히스토리 포함, system prompt DB 조회, JSON 응답 파싱 |
| 설문 생성 | `POST /api/surveys/generate` | 프로젝트 컨텍스트 기반 문항 JSON 배열 생성 |
| AI 설문 편집 | `POST /api/surveys/ai-edit` | 기존 문항 + 수정 요청으로 개선된 문항 반환 |
| 시뮬레이션 인사이트 | `GET /api/simulations/insight` | 응답 분포 요약 + 전략 제안 생성 |
| 시뮬레이션 응답 생성 | `POST /api/simulations/control` (start) | BackgroundTasks로 BATCH_SIZE=6개씩 페르소나×문항 응답 생성 |

> `GEMINI_API_KEY` 미설정 시 모든 AI 기능은 규칙 기반 폴백으로 동작합니다.

## Notes

- Default admin: `admin@digital-twin.ai` / `Admin1234!`
- DB 파일: `digital_twin.db` (루트 · gitignore 권장)
- PostgreSQL 전환 시 `.env`의 `DATABASE_URL`만 변경하면 됩니다.
