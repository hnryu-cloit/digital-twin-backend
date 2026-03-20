import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.mock_store import store

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(body: AssistantChatRequest, _: str = Depends(get_current_user_id)):
    session_id = body.session_id or f"chat-{uuid.uuid4().hex[:8]}"
    messages = store.chat_sessions.setdefault(session_id, [])
    messages.append({"role": "user", "message": body.message})

    answer = "현재 프로젝트 기준으로 구매 의향이 높은 세그먼트는 MZ 얼리어답터이며, AI 카메라 효용 메시지가 가장 효과적입니다."
    messages.append({"role": "assistant", "message": answer})

    return AssistantChatResponse(
        session_id=session_id,
        answer=answer,
        evidence=[
            {"label": "구매 의향", "value": "68.7%"},
            {"label": "응답 정합성", "value": "98.4%"},
        ],
        confidence=92,
    )
