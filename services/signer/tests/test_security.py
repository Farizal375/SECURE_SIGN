"""Test B1 — autentikasi antar-layanan (PRD §9) + requestId/logging.

Konvensi: secret diambil dari env per-request (app/security/auth.py),
maka test cukup men-set env sebelum import app. plaintransport ASGI
tidak menjalankan lifespan; startup check diuji terpisah di B4-verify.
"""

import os

os.environ.setdefault("SIGNER_SERVICE_SECRET", "test-secret-minimal-32-karakter-00")

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security import auth

pytestmark = pytest.mark.anyio

SECRET = os.environ["SIGNER_SERVICE_SECRET"]
HEADERS = {auth.HEADER_NAME: SECRET}


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_health_tanpa_header_tetap_200():
    async with await _client() as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers.get("X-Request-ID")


async def test_endpoint_proteksi_tanpa_header_401():
    # /sign belum ada (baru di B6), tapi middleware berjalan SEBELUM routing,
    # maka request tanpa secret WAJIB 401 — bukan 404.
    async with await _client() as c:
        r = await c.post("/sign", json={})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


async def test_endpoint_proteksi_secret_salah_401():
    async with await _client() as c:
        r = await c.post("/sign", json={}, headers={auth.HEADER_NAME: "salah"})
    assert r.status_code == 401


async def test_endpoint_proteksi_secret_benar_lolos_middleware():
    # Route /sign belum ada -> yang penting BUKAN 401 (lolos auth, 404 dari router).
    # CATATAN B6: saat /sign sudah ada, ubah ekspektasi ini jadi 422 untuk body kosong.
    async with await _client() as c:
        r = await c.post("/sign", json={}, headers=HEADERS)
    assert r.status_code != 401
    assert r.headers.get("X-Request-ID")


async def test_secret_server_kosong_semua_ditolak(monkeypatch):
    # Fail-closed: secret server kosong -> 500 meski header "benar".
    monkeypatch.setenv("SIGNER_SERVICE_SECRET", "")
    async with await _client() as c:
        r = await c.post("/sign", json={}, headers=HEADERS)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "SERVICE_MISCONFIGURED"


def test_is_authorized_unit():
    assert auth.is_authorized(SECRET) is True
    assert auth.is_authorized(None) is False
    assert auth.is_authorized("") is False
    assert auth.is_authorized("salah") is False
    # Secret hampir-sama (beda 1 char, panjang sama) tetap False -> timing-safe path.
    mutated = SECRET[:-1] + ("A" if SECRET[-1] != "A" else "B")
    assert auth.is_authorized(mutated) is False
