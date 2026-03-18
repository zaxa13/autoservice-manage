import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from app.config import settings
from app.api.v1 import api_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Autoservice Management API")
    logger.info(f"SECRET_KEY configured: {bool(settings.SECRET_KEY)}, length: {len(settings.SECRET_KEY) if settings.SECRET_KEY else 0}")
    logger.info(f"ALGORITHM: {settings.ALGORITHM}")
    logger.info(f"ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
    if not settings.SECRET_KEY or not settings.SECRET_KEY.strip():
        logger.error("CRITICAL: SECRET_KEY не установлен или пустой!")
    yield
    logger.info("Shutting down Autoservice Management API")


class RootResponse(BaseModel):
    message: str = Field(..., description="Приветственное сообщение API")
    version: str = Field(..., description="Версия API")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Статус сервиса (ok)")
    secret_key_configured: bool = Field(..., description="Настроен ли SECRET_KEY")


app = FastAPI(
    title="Autoservice Management API",
    description=(
        "REST API для управления автосервисом.\n\n"
        "Функциональность:\n"
        "- Управление клиентами, транспортными средствами и заказ-нарядами\n"
        "- Справочники работ и запчастей\n"
        "- Складской учёт с приходными накладными\n"
        "- Расчёт зарплаты сотрудников\n"
        "- Запись клиентов на обслуживание\n"
        "- Интеграции: YooKassa (платежи), ГИБДД (проверка ТС), поставщики запчастей\n"
        "- Дашборд с аналитикой\n\n"
        "Авторизация через JWT Bearer Token (получить через `POST /api/v1/auth/login`)."
    ),
    version="1.0.0",
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

app.include_router(api_router, prefix="/api/v1")


@app.get(
    "/",
    response_model=RootResponse,
    status_code=status.HTTP_200_OK,
    summary="Корневой эндпоинт",
    description="Возвращает информацию о версии API.",
    tags=["system"],
)
def root():
    return {"message": "Autoservice Management API", "version": "1.0.0"}


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Проверка здоровья",
    description="Health-check эндпоинт для мониторинга. Проверяет доступность сервиса и конфигурацию.",
    tags=["system"],
)
def health_check():
    return {"status": "ok", "secret_key_configured": bool(settings.SECRET_KEY)}
