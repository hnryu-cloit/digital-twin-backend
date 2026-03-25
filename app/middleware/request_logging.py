import json
import logging
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


logger = logging.getLogger("app.request")

SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie"}
SENSITIVE_FIELDS = {"password", "token", "access_token", "refresh_token", "authorization", "secret", "api_key"}


def _mask_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        if len(value) <= 6:
            return "***"
        return f"{value[:2]}***{value[-2:]}"
    return "***"


def _sanitize_data(data: Any) -> Any:
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in SENSITIVE_FIELDS:
                sanitized[key] = _mask_value(value)
            else:
                sanitized[key] = _sanitize_data(value)
        return sanitized
    if isinstance(data, list):
        return [_sanitize_data(item) for item in data]
    return data


async def _extract_json_body(request: Request) -> dict[str, Any] | list[Any] | None:
    if request.method not in {"POST", "PUT", "PATCH"}:
        return None
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return None
    body = await request.body()
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: (_mask_value(value) if key.lower() in SENSITIVE_HEADERS else value)
        for key, value in headers.items()
    }


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        raw_body = await _extract_json_body(request)
        sanitized_body = _sanitize_data(raw_body) if raw_body is not None else None
        sanitized_headers = _sanitize_headers(dict(request.headers.items()))

        logger.info(
            "request.started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "headers": sanitized_headers,
                "body": sanitized_body,
            },
        )

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["x-request-id"] = request_id

        logger.info(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
