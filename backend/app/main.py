import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import api_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Проверка конфигурации при старте"""
    logger.info("Starting Autoservice Management API")
    logger.info(f"SECRET_KEY configured: {bool(settings.SECRET_KEY)}, length: {len(settings.SECRET_KEY) if settings.SECRET_KEY else 0}")
    logger.info(f"ALGORITHM: {settings.ALGORITHM}")
    logger.info(f"ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
    if not settings.SECRET_KEY or not settings.SECRET_KEY.strip():
        logger.error("CRITICAL: SECRET_KEY не установлен или пустой!")
    yield
    logger.info("Shutting down Autoservice Management API")


app = FastAPI(
    title="Autoservice Management API",
    description="API для управления автосервисом",
    version="1.0.0",
    lifespan=lifespan
)

# Простой CORS - разрешаем все для разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Autoservice Management API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok", "secret_key_configured": bool(settings.SECRET_KEY)}
