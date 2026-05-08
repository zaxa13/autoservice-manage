"""FastAPI application для tenant-app в shared-DB архитектуре.

Lifespan ничего не сидит — провижининг тенанта (создание admin user,
системных категорий cashflow и т.п.) делает platform-api при регистрации
через `seed_tenant_defaults`.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
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

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")
