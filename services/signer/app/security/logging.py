"""Logging terstruktur JSON (PRD §15 Observability).

Setiap request dicatat satu baris JSON berisi ``requestId``, ``method``,
``path``, ``status``, ``durationMs``, ``event``. Field ``documentId`` /
``signatureId`` ditambahkan oleh handler endpoint (B6) lewat
``bind_context`` karena middleware generik tidak mengetahuinya.

Sengaja memakai stdlib ``logging`` (tanpa dependensi baru) karena §3
mengunci daftar library.
"""

import contextvars
import json
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "X-Request-ID"

# Context per-request agar handler bisa menempelkan field tambahan ke log.
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "signer_request_id", default="-"
)
extra_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "signer_log_extra", default={}
)


def bind_context(**fields) -> None:
    """Tempel field tambahan (mis. documentId) ke log request berjalan."""
    merged = dict(extra_ctx.get())
    merged.update(fields)
    extra_ctx.set(merged)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "event": getattr(record, "event", record.getMessage()),
            "requestId": getattr(record, "requestId", request_id_ctx.get()),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Konfigurasi root logger sekali saat startup; kembalikan logger 'signer'."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # Redam access log bawaan uvicorn agar tidak duplikat baris JSON kita.
    logging.getLogger("uvicorn.access").disabled = True
    return logging.getLogger("signer")


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    """Tulis satu baris JSON: {"event": ..., "requestId": ..., ...fields}."""
    logger.info(event, extra={"event": event, "extra_fields": fields})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Ukur durasi + catat tiap request sebagai JSON; sematkan X-Request-ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request_id_ctx.set(request_id)
        extra_ctx.set({})
        start = time.perf_counter_ns()
        response = await call_next(request)
        duration_ms = (time.perf_counter_ns() - start) / 1_000_000
        response.headers[REQUEST_ID_HEADER] = request_id
        logger = logging.getLogger("signer")
        log_event(
            logger,
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            durationMs=round(duration_ms, 3),
            **extra_ctx.get(),
        )
        return response
