"""JSON-логирование с request-context для Loki/Promtail/Grafana.

Логи пишутся в stdout (его собирает Promtail из docker-логов). JSON-формат
позволяет в Promtail распарсить поля в labels (service, level, request_id)
и в Grafana фильтровать/группировать без regex по plain-text.
"""

from __future__ import annotations

import logging
import re
import sys
from contextvars import ContextVar
from typing import Any, Iterable, Mapping

from pythonjsonlogger import jsonlogger

from app.config import settings


# ContextVar'ы заполняет middleware на входе запроса. Filter ниже
# подмешивает их в каждую запись лога — так request_id попадает в логи
# из любого сервиса без явного прокидывания.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")
owner_id_var: ContextVar[str] = ContextVar("owner_id", default="")


SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-admin-api-key",
    "proxy-authorization",
}

SENSITIVE_BODY_KEYS = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|"
    r"client[_-]?secret|access[_-]?token|refresh[_-]?token)",
    re.IGNORECASE,
)

MASK = "***"


def mask_headers(headers: Iterable[tuple[str, str]] | Mapping[str, str]) -> dict[str, str]:
    items = headers.items() if isinstance(headers, Mapping) else headers
    out: dict[str, str] = {}
    for k, v in items:
        out[k] = MASK if k.lower() in SENSITIVE_HEADERS else v
    return out


def mask_body(value: Any) -> Any:
    """Рекурсивно маскирует значения по ключам-секретам в dict/list."""
    if isinstance(value, dict):
        return {
            k: (MASK if SENSITIVE_BODY_KEYS.search(k) else mask_body(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [mask_body(v) for v in value]
    return value


class RequestContextFilter(logging.Filter):
    """Подмешивает request_id/tenant_id/owner_id в каждую запись лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        record.tenant_id = tenant_id_var.get() or "-"
        record.owner_id = owner_id_var.get() or "-"
        record.service = settings.log_service_name
        return True


class _JsonFormatter(jsonlogger.JsonFormatter):
    """Чуть кастомизированный JsonFormatter: timestamp в ISO + level в верхнем регистре."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        # jsonlogger заполняет каждое поле из format-строки значением None если
        # его нет на LogRecord — поэтому проверяем truthy, а не `not in`.
        if not log_record.get("timestamp"):
            from datetime import datetime, timezone

            log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())
    if settings.log_format == "json":
        # name убран из формата — оно дублирует logger (оба = record.name).
        # Promtail парсит поля верхнего уровня; вложенные body/headers сохраняются
        # как объекты в общей JSON-строке.
        formatter: logging.Formatter = _JsonFormatter(
            "%(timestamp)s %(level)s %(message)s "
            "%(service)s %(request_id)s %(tenant_id)s %(owner_id)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s "
            "[req=%(request_id)s tenant=%(tenant_id)s] %(message)s"
        )
    handler.setFormatter(formatter)
    return handler


def setup_logging() -> None:
    """Настраивает корневой логгер. Вызывается один раз при старте процесса."""
    root = logging.getLogger()
    # Полностью переопределяем хендлеры — uvicorn/celery могли поставить свои.
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(_build_handler())
    root.setLevel(settings.log_level.upper())

    # uvicorn / sqlalchemy шумят на DEBUG — оставляем INFO, чтобы не топить Loki.
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # uvicorn.error пишет старт/стоп — пусть идёт в наш JSON-хендлер.
    for name in ("uvicorn", "uvicorn.error", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
