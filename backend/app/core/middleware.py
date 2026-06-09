"""ASGI middleware для структурированного логирования HTTP-запросов.

Делает ASGI-обёртку (не BaseHTTPMiddleware), чтобы:
1) Читать request body без блокировки downstream (re-inject через _receive).
2) Перехватывать response body через wrapped send.
3) Корректно работать со streaming-ответами (не буферизуем больше лимита).

На каждый запрос пишутся ровно два события в лог:
- `event=http_request`  — method/path/query/client_ip/headers (и body, если log_http_body).
- `event=http_response` — status/duration_ms/response_headers (и body, если log_http_body).
При exception второй пишется один раз — с уровнем ERROR и exc_info=True.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Optional
from urllib.parse import parse_qsl

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.core.logging import (
    mask_body,
    mask_headers,
    owner_id_var,
    request_id_var,
    tenant_id_var,
)

logger = logging.getLogger("http.access")


def _parse_skip_paths(raw: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in raw.split(",") if p.strip())


SKIP_PATHS = _parse_skip_paths(settings.log_skip_paths)


def _should_skip(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in SKIP_PATHS)


def _decode_body(raw: bytes, content_type: str, max_bytes: int) -> Optional[dict]:
    """Парсит body для лога.

    Возвращает None если body пустое.
    Для JSON и form-urlencoded — парсит с маскировкой секретов.
    Для бинарных/нераспознанных — пишет только размер и truncated.
    `truncated=True` означает что в логе показан только префикс до max_bytes.
    """
    if not raw:
        return None
    truncated = len(raw) > max_bytes
    chunk = raw[:max_bytes]
    if "application/json" in content_type:
        try:
            parsed = json.loads(chunk.decode("utf-8", errors="replace"))
            return {"json": mask_body(parsed), "truncated": truncated}
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    if "application/x-www-form-urlencoded" in content_type:
        try:
            parsed = dict(parse_qsl(chunk.decode("utf-8", errors="replace")))
            return {"form": mask_body(parsed), "truncated": truncated}
        except UnicodeDecodeError:
            pass
    return {"raw_bytes": len(raw), "truncated": truncated}


def _extract_request_id(raw_headers: list[tuple[bytes, bytes]]) -> str:
    """X-Request-ID из входящих headers (для корреляции через несколько сервисов),
    иначе свежий UUID4 hex."""
    for k, v in raw_headers:
        if k == b"x-request-id":
            return v.decode("latin-1")
    return uuid.uuid4().hex


async def _read_full_body(receive: Receive) -> bytes:
    """Считывает весь request body из ASGI receive-канала."""
    chunks: list[bytes] = []
    more_body = True
    while more_body:
        message = await receive()
        if message["type"] != "http.request":
            # disconnect / иное — выходим, downstream получит то что есть.
            break
        chunks.append(message.get("body", b"") or b"")
        more_body = message.get("more_body", False)
    return b"".join(chunks)


class HTTPLoggingMiddleware:
    """ASGI middleware: пишет http_request/http_response в structured-логи.

    Body request/response пишутся целиком до log_body_max_bytes.
    Большие upload'ы режутся (truncated=True), downstream получает полное тело.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if _should_skip(path):
            await self.app(scope, receive, send)
            return

        raw_headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        request_id = _extract_request_id(raw_headers)
        rid_token = request_id_var.set(request_id)
        tid_token = tenant_id_var.set("")
        oid_token = owner_id_var.set("")

        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in raw_headers}
        request_content_type = headers.get("content-type", "")
        client = scope.get("client") or ("-", 0)
        method = scope.get("method", "")
        query = scope.get("query_string", b"").decode("latin-1") or None

        log_body = settings.log_http_body
        max_bytes = settings.log_body_max_bytes

        # Считываем тело и реинжектим — downstream получит ровно то же.
        full_body = await _read_full_body(receive)

        async def replay_receive() -> Message:
            nonlocal full_body
            if full_body is not None:
                msg: Message = {
                    "type": "http.request",
                    "body": full_body,
                    "more_body": False,
                }
                full_body = None  # type: ignore[assignment]
                return msg
            return {"type": "http.disconnect"}

        request_log: dict[str, object] = {
            "event": "http_request",
            "method": method,
            "path": path,
            "query": query,
            "client_ip": client[0],
            "headers": mask_headers(headers),
        }
        if log_body:
            request_log["body"] = _decode_body(full_body, request_content_type, max_bytes)
        logger.info("http_request", extra=request_log)

        response_status = 500
        response_headers: dict[str, str] = {}
        response_body = bytearray()
        body_truncated = False
        start = time.monotonic()

        async def send_wrapper(message: Message) -> None:
            nonlocal response_status, body_truncated
            if message["type"] == "http.response.start":
                response_status = message["status"]
                hdrs = list(message.get("headers") or [])
                hdrs.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": hdrs}
                for k, v in hdrs:
                    response_headers[k.decode("latin-1")] = v.decode("latin-1")
            elif message["type"] == "http.response.body":
                if log_body and len(response_body) < max_bytes:
                    chunk = message.get("body", b"") or b""
                    remaining = max_bytes - len(response_body)
                    response_body.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        body_truncated = True
            await send(message)

        exc: Optional[BaseException] = None
        try:
            await self.app(scope, replay_receive, send_wrapper)
        except BaseException as e:
            exc = e
            raise
        finally:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            response_log: dict[str, object] = {
                "event": "http_response",
                "method": method,
                "path": path,
                "status": 500 if exc is not None else response_status,
                "duration_ms": elapsed_ms,
                "response_headers": mask_headers(response_headers),
            }
            if log_body:
                resp_ct = response_headers.get("content-type", "")
                response_log["body"] = _decode_body(
                    bytes(response_body), resp_ct, max_bytes
                )
                response_log["body_truncated"] = body_truncated

            if exc is not None:
                # exc_info=True добавит traceback в JSON-поле "exc_info".
                logger.error("http_response", extra=response_log, exc_info=True)
            elif response_status >= 500:
                logger.warning("http_response", extra=response_log)
            else:
                logger.info("http_response", extra=response_log)

            request_id_var.reset(rid_token)
            tenant_id_var.reset(tid_token)
            owner_id_var.reset(oid_token)
