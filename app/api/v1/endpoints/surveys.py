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
from app.services.db_store import store

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.post("/generate", response_model=SurveyQuestionListResponse)
async def generate_survey(body: SurveyGenerateRequest, _: str = Depends(get_current_user_id)):
    if not store.get_project(body.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

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
    return SurveyQuestionListResponse(project_id=body.project_id, questions=[SurveyQuestionResponse(**item) for item in store.replace_survey_questions(body.project_id, generated)])


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

    diff: list[str] = []
    updated_questions = []
    for question in questions:
        next_question = dict(question)
        if body.target_question_id is None or question["id"] == body.target_question_id:
            next_question["text"] = f"{question['text']} / {body.prompt}"
            diff.append(f"{question['id']} updated")
        updated_questions.append(next_question)
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
