"""ASGI middleware для структурированного логирования HTTP-запросов.

Делает ASGI-обёртку (не BaseHTTPMiddleware), чтобы:
1) Читать request body без блокировки downstream (re-inject через _receive).
2) Перехватывать response body через wrapped send.
3) Корректно работать со streaming-ответами (не буферизуем больше лимита).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Awaitable, Callable

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


def _decode_body(raw: bytes, content_type: str, max_bytes: int) -> object:
    """Парсит body для лога: JSON → dict (маскировка), иначе truncated str."""
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
        # Form'у тоже маскируем — там часто пароли.
        from urllib.parse import parse_qsl

        try:
            parsed = dict(parse_qsl(chunk.decode("utf-8", errors="replace")))
            return {"form": mask_body(parsed), "truncated": truncated}
        except Exception:
            pass
    # Бинарь или нераспознанный текст — не пишем содержимое, только размер.
    return {"raw_bytes": len(raw), "truncated": truncated}


class HTTPLoggingMiddleware:
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

        # request_id: либо принимаем из X-Request-ID (для трейса через несколько сервисов),
        # либо генерим. UUID4 короче и достаточно для корреляции в Loki.
        raw_headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        incoming_rid = ""
        for k, v in raw_headers:
            if k == b"x-request-id":
                incoming_rid = v.decode("latin-1")
                break
        request_id = incoming_rid or uuid.uuid4().hex
        rid_token = request_id_var.set(request_id)
        tid_token = tenant_id_var.set("")
        oid_token = owner_id_var.set("")

        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in raw_headers}
        content_type = headers.get("content-type", "")
        client = scope.get("client") or ("-", 0)

        log_body = settings.log_http_body
        max_bytes = settings.log_body_max_bytes

        # Читаем request body целиком и реинжектим, чтобы downstream увидел его.
        # Для очень больших body (upload файлов) — body_log будет truncated.
        body_chunks: list[bytes] = []
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body_chunks.append(message.get("body", b"") or b"")
                more_body = message.get("more_body", False)
            else:
                # disconnect и пр. — пропускаем дальше как есть.
                break
        full_body = b"".join(body_chunks)

        async def replay_receive() -> Message:
            # Один раз отдаём весь буфер; дальнейшие вызовы — disconnect.
            nonlocal full_body
            if full_body is not None:
                msg = {"type": "http.request", "body": full_body, "more_body": False}
                full_body = None  # type: ignore[assignment]
                return msg
            return {"type": "http.disconnect"}

        request_log: dict[str, object] = {
            "event": "http_request",
            "method": scope.get("method"),
            "path": path,
            "query": scope.get("query_string", b"").decode("latin-1") or None,
            "client_ip": client[0],
            "headers": mask_headers(headers),
        }
        if log_body:
            request_log["body"] = _decode_body(full_body, content_type, max_bytes)
        logger.info("http_request", extra=request_log)

        # Перехватываем send: ловим status, response headers, аккумулируем body
        # до лимита (стримим дальше всё что приходит — не буферизуем сверху).
        response_status = 500
        response_headers: dict[str, str] = {}
        response_body = bytearray()
        captured_full = True
        start = time.monotonic()

        async def send_wrapper(message: Message) -> None:
            nonlocal response_status, captured_full
            if message["type"] == "http.response.start":
                response_status = message["status"]
                hdrs = message.get("headers") or []
                # Добавляем X-Request-ID в ответ для клиентской корреляции.
                hdrs = list(hdrs) + [(b"x-request-id", request_id.encode("latin-1"))]
                message = {**message, "headers": hdrs}
                for k, v in hdrs:
                    response_headers[k.decode("latin-1")] = v.decode("latin-1")
            elif message["type"] == "http.response.body":
                if log_body and len(response_body) < max_bytes:
                    chunk = message.get("body", b"") or b""
                    remaining = max_bytes - len(response_body)
                    response_body.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        captured_full = False
            await send(message)

        try:
            await self.app(scope, replay_receive, send_wrapper)
        except Exception:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            logger.exception(
                "http_request_failed",
                extra={
                    "event": "http_response",
                    "method": scope.get("method"),
                    "path": path,
                    "status": 500,
                    "duration_ms": elapsed_ms,
                },
            )
            raise
        finally:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            response_log: dict[str, object] = {
                "event": "http_response",
                "method": scope.get("method"),
                "path": path,
                "status": response_status,
                "duration_ms": elapsed_ms,
                "response_headers": mask_headers(response_headers),
            }
            if log_body:
                resp_ct = response_headers.get("content-type", "")
                response_log["body"] = _decode_body(
                    bytes(response_body), resp_ct, max_bytes
                )
                response_log["body_truncated"] = not captured_full
            log_level = logging.WARNING if response_status >= 500 else logging.INFO
            logger.log(log_level, "http_response", extra=response_log)
            request_id_var.reset(rid_token)
            tenant_id_var.reset(tid_token)
            owner_id_var.reset(oid_token)
