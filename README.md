# digital-twin-backend

> **⚠️ 전역 시스템 제약조건 및 코드 컨벤션**
> 본 프로젝트는 엔터프라이즈 B2B SaaS 아키텍처를 지향하며, 엄격한 코드 컨벤션을 따릅니다.
> 자세한 사항은 루트 디렉토리의 [`docs/conventions.md`](../docs/conventions.md)를 반드시 확인하세요.
> 주요 백엔드 제약: **Layered Architecture (Router-Service-Repo), FastAPI + Pydantic v2, Ruff & Mypy Strict**

Samsung Digital Customer Twin FastAPI backend

## Stack

- **Python 3.9+** / FastAPI / Uvicorn
- **PostgreSQL** (asyncpg + SQLAlchemy 2.0 async)
- **Alembic** for DB migrations
- **Gemini API** for AI integration

## Structure

```
app/
├── api/v1/endpoints/   # API routers
├── core/               # config, dependencies, security
├── models/             # SQLAlchemy models
├── schemas/            # Pydantic schemas
├── services/           # domain services / mock store
└── main.py             # FastAPI entrypoint
```

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

uvicorn app.main:app --reload
```

Docs: `http://localhost:8000/docs`

## Current API Shape

- Base prefix: `/api`
- Auth: `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`
- Projects: `/api/projects`
- Personas: `/api/personas`, `/api/personas/pool`
- Segments: `/api/segments/aggregate`, `/api/segments/chart`, `/api/segments/kpi`
- Surveys: `/api/surveys/generate`, `/api/surveys/{project_id}/questions`, `/api/surveys/confirm`
- Simulations: `/api/simulations/control`, `/api/simulations/progress`, `/api/simulations/feed`
- Reports: `/api/reports`, `/api/reports/generate`
- Assistant: `/api/assistant/chat`
- Settings: `/api/settings/prompts`, `/api/settings/llm-parameters`

## Notes

- The current implementation is an in-memory backend aligned to `feature list/backend.csv` P0-first flows.
- Existing SQLAlchemy models remain in the repo for the later PostgreSQL migration step.
- Default seed admin:
  - email: `admin@digital-twin.ai`
  - password: `Admin1234!`
