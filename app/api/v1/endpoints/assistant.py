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


def _build_fallback_chat_response() -> tuple[str, list[dict[str, str]], int]:
    projects = store.list_projects()
    project = projects[0] if projects else None
    if not project:
        return (
            "현재 연결된 프로젝트 데이터가 없어 분석 요약을 생성할 수 없습니다.",
            [{"label": "프로젝트 상태", "value": "데이터 없음"}],
            40,
        )

    personas = store.list_personas(project["id"])
    reports = store.list_reports(project["id"])
    simulation = store.get_simulation(project["id"])
    top_segment = "데이터 없음"
    if personas:
        segment_counts: dict[str, int] = {}
        for persona in personas:
            segment = persona.get("segment") or "미분류"
            segment_counts[segment] = segment_counts.get(segment, 0) + 1
        top_segment = sorted(segment_counts.items(), key=lambda item: item[1], reverse=True)[0][0]

    answer = (
        f"현재 프로젝트 '{project['name']}' 기준으로 가장 큰 세그먼트는 {top_segment}이며, "
        f"응답 진행률은 {project.get('progress', 0)}%입니다."
    )
    evidence = [
        {"label": "프로젝트", "value": project["name"]},
        {"label": "페르소나 수", "value": str(len(personas))},
        {"label": "리포트 수", "value": str(len(reports))},
    ]
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
            # 최근 6개 대화 이력을 컨텍스트로 포함
            recent = messages[-6:] if len(messages) >= 6 else messages[:]
            history_text = "\n".join(
                f"{'사용자' if m['role'] == 'user' else '어시스턴트'}: {m['message']}"
                for m in recent[:-1]  # 마지막(현재 질문) 제외
            )
            prompt = f"""시스템 지시: {system_prompt}

{'대화 이력:' + chr(10) + history_text if history_text else ''}

사용자 질문: {body.message}

다음 JSON만 출력하세요:
{{"answer": "답변 내용", "evidence": [{{"label": "근거 레이블", "value": "근거 값"}}], "confidence": 85}}"""

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

    answer, evidence, confidence = _build_fallback_chat_response()
    messages.append({"role": "assistant", "message": answer})

    return AssistantChatResponse(
        session_id=session_id,
        answer=answer,
        evidence=evidence,
        confidence=confidence,
    )
