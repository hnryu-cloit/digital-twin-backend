import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router
from app.core.config import settings
from app.middleware.request_logging import RequestLoggingMiddleware
from app.schemas.common import ErrorResponse, HealthStatusResponse
from app.services.db_store import init_db


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s request_id=%(request_id)s",
)
logging.getLogger().addFilter(RequestContextFilter())

app = FastAPI(title=settings.APP_NAME, version="0.1.0")


@app.on_event("startup")
def on_startup():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    body = ErrorResponse(code=f"HTTP_{exc.status_code}", message=message, detail=message)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


app.include_router(router)


@app.get("/health", response_model=HealthStatusResponse)
async def health():
    llm_status = "connected" if settings.GEMINI_API_KEY else "not_configured"
    return HealthStatusResponse(status="ok", database="sqlite", llm=llm_status)
