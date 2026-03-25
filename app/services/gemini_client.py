"""Gemini API 클라이언트 - API 키 없을 때는 None 반환하는 안전한 래퍼."""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)
_model = None


def _get_model():
    """지연 초기화 - 첫 호출 시만 초기화."""
    global _model
    if _model is not None:
        return _model
    if not settings.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-3.0-flash")
        logger.info("Gemini 초기화 완료")
        return _model
    except Exception as e:
        logger.warning("Gemini 초기화 실패: %s", e)
        return None


def is_available() -> bool:
    return _get_model() is not None


def generate(prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> Optional[str]:
    """텍스트 생성. 실패 시 None 반환."""
    model = _get_model()
    if model is None:
        return None
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
        )
        return response.text
    except Exception as e:
        logger.error("Gemini 생성 오류: %s", e)
        return None
