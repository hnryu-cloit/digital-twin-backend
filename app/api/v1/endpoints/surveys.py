import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from app.core.dependencies import get_current_user_id
from app.schemas.ai_job import AIJobResponse
from app.schemas.survey import (
    SurveyAiUpdateResponse,
    SurveyConfirmRequest,
    SurveyGenerateJobRequest,
    SurveyGenerateRequest,
    SurveyQuestionListResponse,
    SurveyQuestionRequest,
    SurveyQuestionResponse,
    SurveyUpdateWithAiRequest,
)
from app.services import gemini_client
from app.services.db_store import store

router = APIRouter(prefix="/surveys", tags=["surveys"])


def _fallback_question_templates(survey_type: str) -> list[tuple[str, list[str]]]:
    templates = {
        "concept": [
            ("이 컨셉의 첫인상은 어떻습니까?", ["매우 긍정적", "긍정적", "보통", "부정적", "매우 부정적"]),
            ("가장 매력적으로 느껴지는 요소는 무엇입니까?", ["핵심 기능", "디자인", "브랜드 신뢰", "가격 경쟁력"]),
            ("실제 구매를 고려하게 만드는 요인은 무엇입니까?", ["성능", "편의성", "가격", "추천/후기"]),
            ("이 컨셉에서 가장 우려되는 점은 무엇입니까?", ["가격", "복잡성", "차별성 부족", "신뢰성"]),
        ],
        "ad": [
            ("광고 메시지가 제품의 강점을 명확히 전달합니까?", ["매우 그렇다", "그렇다", "보통", "아니다", "전혀 아니다"]),
            ("광고를 본 뒤 기억에 남는 요소는 무엇입니까?", ["카피", "비주얼", "혜택", "브랜드"]),
            ("광고 노출 후 구매 의향 변화는 어떻습니까?", ["매우 상승", "상승", "변화 없음", "하락"]),
            ("광고 메시지에서 보완이 필요한 부분은 무엇입니까?", ["차별성", "신뢰성", "혜택 설명", "타깃 적합성"]),
        ],
    }
    return templates.get(
        survey_type,
        [
            ("이 주제에 대해 얼마나 관심이 있습니까?", ["매우 높다", "높다", "보통", "낮다", "매우 낮다"]),
            ("가장 중요하게 보는 판단 기준은 무엇입니까?", ["품질", "가격", "편의성", "브랜드"]),
            ("구매 또는 참여를 결정하게 만드는 계기는 무엇입니까?", ["추천", "경험", "혜택", "필요성"]),
            ("개선이 필요하다고 느끼는 지점은 무엇입니까?", ["기능", "가격", "설명", "접근성"]),
        ],
    )


def _build_fallback_questions(prompt: str, survey_type: str, question_count: int) -> list[dict]:
    base_templates = _fallback_question_templates(survey_type)
    questions: list[dict] = []
    for index in range(question_count):
        template_text, options = base_templates[index % len(base_templates)]
        questions.append(
            {
                "id": f"q-{uuid.uuid4().hex[:8]}",
                "text": f"{prompt} - {template_text}",
                "type": "단일선택",
                "options": options,
                "order": index + 1,
                "status": "draft",
            }
        )
    return questions


def _compose_generation_prompt(
    user_prompt: str,
    survey_type: str,
    question_count: int,
    template: dict,
    segment_context: dict,
) -> str:
    template_id = template.get("template_id", "template-not-set")
    required_blocks = ", ".join(template.get("required_blocks", [])) or "none"
    segment_summary = json.dumps(segment_context, ensure_ascii=False) if segment_context else "없음"
    return (
        f"{question_count}개 설문 문항을 생성하세요.\n"
        f"유형: {survey_type}\n"
        f"사용자 요청: {user_prompt}\n"
        f"리서치 템플릿 ID: {template_id}\n"
        f"필수 블록: {required_blocks}\n"
        f"세그먼트 분석 컨텍스트: {segment_summary}"
    )


def _generate_questions(
    project_id: str,
    user_prompt: str,
    survey_type: str,
    question_count: int,
    template: dict | None = None,
    segment_context: dict | None = None,
) -> list[dict]:
    generated = None
    template = template or {}
    segment_context = segment_context or {}

    if gemini_client.is_available():
        try:
            prompt = _compose_generation_prompt(
                user_prompt=user_prompt,
                survey_type=survey_type,
                question_count=question_count,
                template=template,
                segment_context=segment_context,
            )
            full_prompt = f"""{prompt}

다음 JSON 배열만 출력하세요:
[{{"text": "문항 텍스트", "type": "단일선택|복수선택|리커트척도|주관식", "options": ["선택지1", "선택지2"]}}]

주의:
- 주관식 문항의 options는 빈 배열 []
- 리커트척도는 ["매우 그렇다", "그렇다", "보통", "아니다", "전혀 아니다"]
- 정확히 {question_count}개 생성"""
            text = gemini_client.generate(full_prompt, temperature=0.7)
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

    if not generated:
        generated = _build_fallback_questions(user_prompt, survey_type, question_count)

    return store.replace_survey_questions(project_id, generated)


def _run_generate_survey_job(job_id: str) -> None:
    job = store.get_ai_job(job_id)
    if job is None or job["status"] == "cancelled":
        return

    payload = job.get("payload", {})
    store.update_ai_job(
        job_id,
        status="running",
        progress=15,
        started_at=datetime.now(timezone.utc),
    )
    try:
        questions = _generate_questions(
            project_id=job["project_id"],
            user_prompt=payload.get("user_prompt", ""),
            survey_type=payload.get("survey_type", "concept"),
            question_count=payload.get("question_count", 5),
            template=payload.get("template", {}),
            segment_context=payload.get("segment_context", {}),
        )
        store.update_ai_job(
            job_id,
            status="completed",
            progress=100,
            result_ref={
                "resource": "survey_questions",
                "project_id": job["project_id"],
                "question_count": len(questions),
            },
            completed_at=datetime.now(timezone.utc),
        )
    except Exception as error:
        store.update_ai_job(
            job_id,
            status="failed",
            progress=100,
            error_code="SURVEY_GENERATION_FAILED",
            error_message=str(error),
            completed_at=datetime.now(timezone.utc),
        )


@router.post("/generate-job", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_survey_job(
    body: SurveyGenerateJobRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    if not store.get_project(body.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    job = store.create_ai_job(
        project_id=body.project_id,
        job_type="survey_generate",
        payload=body.model_dump(),
        created_by=user_id,
    )
    background_tasks.add_task(_run_generate_survey_job, job["id"])
    return AIJobResponse(**job)


@router.post("/generate", response_model=SurveyQuestionListResponse)
async def generate_survey(body: SurveyGenerateRequest, _: str = Depends(get_current_user_id)):
    if not store.get_project(body.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    generated = _generate_questions(
        project_id=body.project_id,
        user_prompt=body.prompt,
        survey_type=body.survey_type,
        question_count=body.question_count,
    )
    return SurveyQuestionListResponse(
        project_id=body.project_id,
        questions=[SurveyQuestionResponse(**item) for item in generated],
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

    if updated_questions is None:
        diff: list[str] = []
        updated_questions = []
        for question in questions:
            next_question = dict(question)
            if body.target_question_id is None or question["id"] == body.target_question_id:
                next_question["text"] = f"{question['text']} ({body.prompt})"
                diff.append(f"{question['id']} revised")
            updated_questions.append(next_question)
    else:
        diff = [f"{q['id']} revised" for q in updated_questions]

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
