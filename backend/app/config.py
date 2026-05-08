"""Конфигурация tenant-app для shared-DB архитектуры.

Подключения:
    DATABASE_URL          — рантайм, asyncpg, роль tenant_app, через pgbouncer
                            transaction-pool. Используется во всех HTTP-запросах
                            и Celery-тасках через `tenant_session(tenant_id)`.
    DATABASE_URL_MIGRATOR — Alembic, psycopg2, роль migrator_app, через pgbouncer
                            session-pool. Используется только из CLI миграций.

SQLite больше не поддерживается: RLS, composite FK, IDENTITY-колонки и
GUC-переменные — всё Postgres-only.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database — runtime (async)
    DATABASE_URL: str = (
        "postgresql+asyncpg://tenant_app:change-me@localhost:6432/autoworks_tx"
    )
    # Database — Alembic (sync, BYPASSRLS role)
    DATABASE_URL_MIGRATOR: str = (
        "postgresql+psycopg2://migrator_app:change-me@localhost:6432/autoworks_session"
    )

    # JWT (общий секрет с platform-api: токен подписывается там, валидируется здесь).
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # ЮKassa (для приёма платежей внутри tenant-приложения, если используется)
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""

    # SMS
    SMS_API_KEY: str = ""
    SMS_SENDER: str = "Autoservice"

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""

    # Frontend URL (используется в ссылках для сброса пароля)
    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Поставщики
    PARTS_SUPPLIER_API_KEY: str = ""
    PARTS_SUPPLIER_API_URL: str = ""

    # ГИБДД
    GIBDD_API_KEY: str = ""
    GIBDD_API_URL: str = ""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
