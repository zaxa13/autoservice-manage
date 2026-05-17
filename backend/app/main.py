"""FastAPI application для tenant-app в shared-DB архитектуре.

Lifespan ничего не сидит — провижининг тенанта (создание admin user,
системных категорий cashflow и т.п.) делает platform-api при регистрации
через `seed_tenant_defaults`.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.v1 import api_router
from app.config import settings
from app.database import dispose_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Autoservice Management API")
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        logger.error("SECRET_KEY missing or too short — JWT validation will fail")
    yield
    logger.info("Shutting down — disposing engine")
    await dispose_engine()


class HealthResponse(BaseModel):
    status: str = Field(..., description="Статус сервиса (ok)")


app = FastAPI(
    title="Autoservice Management API",
    version="2.0.0",
    description="REST API для управления автосервисом (shared-DB архитектура).",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def _flatten_validation_error(request: Request, exc: RequestValidationError):
    """Возвращает 422 в том же формате `{"detail": "<строка>"}` что и 400/404.

    По умолчанию FastAPI отдаёт `detail` как массив ошибок Pydantic, что:
      1) ломает фронт (он ждёт строку и валится на render объекта);
      2) ничего не говорит пользователю.

    Собираем сообщения в одну строку через "; ".
    """
    messages: list[str] = []
    for err in exc.errors():
        msg = err.get("msg") or "Некорректный запрос"
        # У Pydantic v2 сообщение часто префиксится "Value error, …" — обрежем.
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        messages.append(msg)
    detail = "; ".join(messages) if messages else "Некорректный запрос"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")
