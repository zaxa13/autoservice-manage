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

    # Logging — JSON-формат для Loki/Promtail.
    # log_http_body=True — пишем request/response body в access-лог (для дебага
    # клиентских жалоб через Grafana). Чувствительные ключи (password/token/secret/
    # access_token/refresh_token/api_key) маскируются автоматически — см. SENSITIVE_*
    # в core/logging.py. Body режется до log_body_max_bytes, оставшееся помечается
    # truncated=true. Отключить при необходимости через env: log_http_body=false
    # (lowercase, т.к. case_sensitive=True в SettingsConfigDict).
    log_level: str = "INFO"
    log_format: str = "json"  # json | text
    log_service_name: str = "tenant-app"
    log_http_body: bool = True
    log_body_max_bytes: int = 8192
    log_skip_paths: str = "/health,/docs,/openapi.json,/redoc"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
