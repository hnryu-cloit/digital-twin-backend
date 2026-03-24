import json
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.dependencies import get_current_user_id
from app.schemas.survey import (
    SurveyAiUpdateResponse,
    SurveyConfirmRequest,
    SurveyGenerateRequest,
    SurveyQuestionListResponse,
    SurveyQuestionRequest,
    SurveyQuestionResponse,
    SurveyUpdateWithAiRequest,
)
from app.services import gemini_client
from app.services.db_store import store

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.post("/generate", response_model=SurveyQuestionListResponse)
async def generate_survey(body: SurveyGenerateRequest, _: str = Depends(get_current_user_id)):
    if not store.get_project(body.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    generated = None

    # Gemini로 실제 문항 생성 시도
    if gemini_client.is_available():
        try:
            prompt = f"""{body.question_count}개 설문 문항을 생성하세요.
유형: {body.survey_type}
목적: {body.prompt}

다음 JSON 배열만 출력하세요:
[{{"text": "문항 텍스트", "type": "단일선택|복수선택|리커트척도|주관식", "options": ["선택지1", "선택지2"]}}]

주의:
- 주관식 문항의 options는 빈 배열 []
- 리커트척도는 ["매우 그렇다", "그렇다", "보통", "아니다", "전혀 아니다"]
- 정확히 {body.question_count}개 생성"""

            text = gemini_client.generate(prompt, temperature=0.7)
            if text:
                pattern = r"\[.*\]"
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, list) and len(parsed) > 0:
                        generated = []
                        for index, item in enumerate(parsed, start=1):
                            if isinstance(item, dict) and "text" in item:
                                question_type = item.get("type", "단일선택")
                                generated.append({
                                    "id": f"q-{uuid.uuid4().hex[:8]}",
                                    "text": item["text"],
                                    "type": question_type,
                                    "options": item.get("options", []) if question_type != "주관식" else [],
                                    "order": index,
                                    "status": "draft",
                                })
        except Exception:
            generated = None

    # 폴백 로직
    if not generated:
        generated = []
        for index in range(1, body.question_count + 1):
            question_type = ["단일선택", "복수선택", "리커트척도", "주관식"][(index - 1) % 4]
            generated.append(
                {
                    "id": f"q-{uuid.uuid4().hex[:8]}",
                    "text": f"{body.prompt} 관련 자동 생성 문항 {index}",
                    "type": question_type,
                    "options": [] if question_type == "주관식" else ["매우 그렇다", "그렇다", "보통", "아니다"],
                    "order": index,
                    "status": "draft",
                }
            )

    return SurveyQuestionListResponse(
        project_id=body.project_id,
        questions=[SurveyQuestionResponse(**item) for item in store.replace_survey_questions(body.project_id, generated)],
    )


@router.post("/{project_id}/questions", response_model=SurveyQuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    project_id: str,
    body: SurveyQuestionRequest,
    _: str = Depends(get_current_user_id),
):
    questions = store.list_survey_questions(project_id)
    if not store.get_project(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    question = {
        "id": f"q-{uuid.uuid4().hex[:8]}",
        "text": body.text,
        "type": body.type,
        "options": body.options,
        "order": len(questions) + 1,
        "status": "draft",
    }
    questions.append(question)
    store.replace_survey_questions(project_id, questions)
    return SurveyQuestionResponse(**question)


@router.get("/{project_id}/questions", response_model=SurveyQuestionListResponse)
async def list_questions(project_id: str, _: str = Depends(get_current_user_id)):
    return SurveyQuestionListResponse(
        project_id=project_id,
        questions=[SurveyQuestionResponse(**item) for item in store.list_survey_questions(project_id)],
    )


@router.patch("/{project_id}/ai-edit", response_model=SurveyAiUpdateResponse)
async def ai_edit_survey(
    project_id: str,
    body: SurveyUpdateWithAiRequest,
    _: str = Depends(get_current_user_id),
):
    questions = store.list_survey_questions(project_id)
    if not questions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found.")

    updated_questions = None

    # Gemini로 실제 문항 수정 시도
    if gemini_client.is_available():
        try:
            target_questions = (
                [q for q in questions if q["id"] == body.target_question_id]
                if body.target_question_id
                else questions
            )
            questions_json = json.dumps(
                [{"id": q["id"], "text": q["text"], "type": q["type"], "options": q["options"]} for q in target_questions],
                ensure_ascii=False,
            )
            prompt = f"""다음 설문 문항들을 수정 요청에 맞게 개선하세요.

기존 문항:
{questions_json}

수정 요청: {body.prompt}

다음 JSON 배열만 출력하세요 (id, text, type, options 필드 포함):
[{{"id": "기존 id", "text": "개선된 문항 텍스트", "type": "기존 type", "options": [...]}}]"""

            text = gemini_client.generate(prompt, temperature=0.7)
            if text:
                pattern = r"\[.*\]"
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, list):
                        parsed_map = {item["id"]: item for item in parsed if isinstance(item, dict) and "id" in item}
                        updated_questions = []
                        for q in questions:
                            if q["id"] in parsed_map:
                                merged = {**q, **parsed_map[q["id"]]}
                                updated_questions.append(merged)
                            else:
                                updated_questions.append(dict(q))
        except Exception:
            updated_questions = None

    # 폴백 로직
    if updated_questions is None:
        diff: list[str] = []
        updated_questions = []
        for question in questions:
            next_question = dict(question)
            if body.target_question_id is None or question["id"] == body.target_question_id:
                next_question["text"] = f"{question['text']} / {body.prompt}"
                diff.append(f"{question['id']} updated")
            updated_questions.append(next_question)
    else:
        diff = [f"{q['id']} updated" for q in updated_questions]

    store.replace_survey_questions(project_id, updated_questions)

    return SurveyAiUpdateResponse(
        project_id=project_id,
        questions=[SurveyQuestionResponse(**item) for item in updated_questions],
        diff=diff,
    )


@router.post("/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_survey(body: SurveyConfirmRequest, _: str = Depends(get_current_user_id)):
    questions = store.list_survey_questions(body.project_id)
    if not questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one question is required.")
    confirmed = [{**item, "status": "confirmed"} for item in questions]
    store.replace_survey_questions(body.project_id, confirmed)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/preview", response_model=SurveyQuestionListResponse)
async def preview_survey(project_id: str, _: str = Depends(get_current_user_id)):
    return SurveyQuestionListResponse(
        project_id=project_id,
        questions=[SurveyQuestionResponse(**item) for item in store.list_survey_questions(project_id)],
    )