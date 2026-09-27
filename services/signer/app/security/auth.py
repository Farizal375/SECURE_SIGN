"""Autentikasi antar-layanan (PRD §9).

Setiap request apps/web (server-side) -> signer WAJIB membawa header
``X-Signer-Service-Secret``. Perbandingan memakai ``hmac.compare_digest``
(bukan ``==``) agar tahan timing attack. Tanpa header valid -> 401.
Endpoint internal DILARANG diekspos ke browser/publik.

Fail-closed: bila secret server kosong/belum dikonfigurasi, SEMUA request
proteksi ditolak (500), tidak pernah diloloskan.
"""

import hmac
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

HEADER_NAME = "X-Signer-Service-Secret"

# Path yang boleh diakses tanpa secret (liveness + dokumentasi dev).
# Semua path lain WAJIB membawa header valid.
EXEMPT_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})


def get_service_secret() -> str:
    """Baca secret dari environment per-request (mendukung rotasi tanpa restart)."""
    return os.environ.get("SIGNER_SERVICE_SECRET", "")


def is_authorized(provided: str | None) -> bool:
    """True hanya bila secret server terkonfigurasi DAN cocok timing-safe."""
    expected = get_service_secret()
    if not expected or not provided:
        return False
    try:
        return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
    except (TypeError, UnicodeEncodeError):
        return False


def unauthorized_response() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Missing or invalid X-Signer-Service-Secret",
            }
        },
    )


def misconfigured_response() -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "SERVICE_MISCONFIGURED",
                "message": "Signer service secret is not configured",
            }
        },
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware §9: tolak request tanpa header valid sebelum sampai router."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        if not get_service_secret():
            # Fail-closed: secret belum diisi -> jangan layani apa pun.
            return misconfigured_response()
        if not is_authorized(request.headers.get(HEADER_NAME)):
            return unauthorized_response()
        return await call_next(request)
