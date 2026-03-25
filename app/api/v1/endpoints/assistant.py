import json
import re
import uuid

from fastapi import APIRouter, Depends

from app.core.defaults import DEFAULT_PROMPTS
from app.core.dependencies import get_current_user_id
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services import gemini_client
from app.services.db_store import store

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _resolve_project(project_id: str | None = None) -> dict | None:
    projects = store.list_projects()
    if project_id:
        return next((item for item in projects if item["id"] == project_id), None)
    if not projects:
        return None
    return max(
        projects,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
    )


def _build_project_context(project_id: str | None = None) -> dict:
    project = _resolve_project(project_id)
    if not project:
        return {}

    personas = store.list_personas(project["id"])
    reports = store.list_reports(project["id"])
    simulation = store.get_simulation(project["id"])
    questions = store.list_survey_questions(project["id"])

    segment_counts: dict[str, int] = {}
    for persona in personas:
        segment = persona.get("segment") or "미분류"
        segment_counts[segment] = segment_counts.get(segment, 0) + 1

    latest_report = reports[0] if reports else None
    report_context = {}
    if latest_report:
        report_context = {
            "title": latest_report.get("title"),
            "summary": latest_report.get("summary"),
            "generated_at": latest_report.get("generated_at"),
        }

    return {
        "project": {
            "id": project["id"],
            "name": project["name"],
            "type": project.get("type"),
            "progress": project.get("progress", 0),
            "response_count": project.get("response_count", 0),
            "target_responses": project.get("target_responses", 0),
        },
        "survey": {
            "question_count": len(questions),
            "confirmed_count": sum(1 for item in questions if item.get("status") == "confirmed"),
            "sample_questions": [item.get("text", "") for item in questions[:3]],
        },
        "personas": {
            "count": len(personas),
            "top_segments": sorted(segment_counts.items(), key=lambda item: item[1], reverse=True)[:3],
        },
        "simulation": simulation or {},
        "latest_report": report_context,
    }


def _build_fallback_chat_response(project_id: str | None = None) -> tuple[str, list[dict[str, str]], int]:
    context = _build_project_context(project_id)
    project = context.get("project")
    if not project:
        return (
            "현재 연결된 프로젝트 데이터가 없어 분석 요약을 생성할 수 없습니다.",
            [{"label": "프로젝트 상태", "value": "데이터 없음"}],
            40,
        )
    top_segments = context.get("personas", {}).get("top_segments", [])
    top_segment = top_segments[0][0] if top_segments else "데이터 없음"

    answer = (
        f"현재 프로젝트 '{project['name']}' 기준으로 가장 큰 세그먼트는 {top_segment}이며, "
        f"응답 진행률은 {project.get('progress', 0)}%입니다."
    )
    evidence = [
        {"label": "프로젝트", "value": project["name"]},
        {"label": "페르소나 수", "value": str(context.get("personas", {}).get("count", 0))},
        {"label": "설문 문항 수", "value": str(context.get("survey", {}).get("question_count", 0))},
    ]
    latest_report = context.get("latest_report")
    if latest_report and latest_report.get("title"):
        evidence.append({"label": "최근 리포트", "value": str(latest_report["title"])})
    simulation = context.get("simulation")
    if simulation:
        evidence.append({"label": "완료 응답", "value": str(simulation.get("completed_responses", 0))})
    return answer, evidence, 78


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(body: AssistantChatRequest, _: str = Depends(get_current_user_id)):
    session_id = body.session_id or f"chat-{uuid.uuid4().hex[:8]}"
    messages = store.chat_sessions.setdefault(session_id, [])
    messages.append({"role": "user", "message": body.message})

    # Gemini로 실제 답변 생성 시도
    if gemini_client.is_available():
        try:
            system_prompt = store.get_setting("prompt:assistant", DEFAULT_PROMPTS["assistant"])
            project_context = _build_project_context(body.project_id)
            # 최근 6개 대화 이력을 컨텍스트로 포함
            recent = messages[-6:] if len(messages) >= 6 else messages[:]
            history_text = "\n".join(
                f"{'사용자' if m['role'] == 'user' else '어시스턴트'}: {m['message']}"
                for m in recent[:-1]  # 마지막(현재 질문) 제외
            )
            prompt = f"""시스템 지시: {system_prompt}

{'대화 이력:' + chr(10) + history_text if history_text else ''}

프로젝트 컨텍스트(JSON):
{json.dumps(project_context, ensure_ascii=False, indent=2)}

사용자 질문: {body.message}

다음 JSON만 출력하세요:
{{"answer": "답변 내용", "evidence": [{{"label": "근거 레이블", "value": "프로젝트 컨텍스트의 실제 값"}}], "confidence": 85}}

주의:
- 프로젝트 컨텍스트에 없는 사실은 추정하지 말 것
- evidence는 반드시 위 JSON 컨텍스트에서 확인 가능한 값만 넣을 것"""

            text = gemini_client.generate(prompt, temperature=0.7)
            if text:
                pattern = r"\{.*\}"
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, dict) and "answer" in parsed:
                        answer = parsed["answer"]
                        evidence = parsed.get("evidence", [])
                        confidence = int(parsed.get("confidence", 85))
                        messages.append({"role": "assistant", "message": answer})
                        return AssistantChatResponse(
                            session_id=session_id,
                            answer=answer,
                            evidence=evidence,
                            confidence=confidence,
                        )
        except Exception:
            pass

    answer, evidence, confidence = _build_fallback_chat_response(body.project_id)
    messages.append({"role": "assistant", "message": answer})

    return AssistantChatResponse(
        session_id=session_id,
        answer=answer,
        evidence=evidence,
        confidence=confidence,
    )
