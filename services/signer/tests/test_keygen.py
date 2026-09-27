"""Test B3 — POST /keygen (keputusan terkunci #2, FR-02/FR-03 via API)."""

import base64
import os
import re

os.environ.setdefault("SIGNER_SERVICE_SECRET", "test-secret-minimal-32-karakter-00")
os.environ.setdefault(
    "PRIVATE_KEY_ENCRYPTION_KEY", base64.b64encode(b"\x01" * 32).decode()
)

import pytest
from cryptography.hazmat.primitives import serialization
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security import auth

pytestmark = pytest.mark.anyio

HEADERS = {auth.HEADER_NAME: os.environ["SIGNER_SERVICE_SECRET"]}


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_keygen_tanpa_header_401():
    async with await _client() as c:
        r = await c.post("/keygen", json={})
    assert r.status_code == 401


async def test_keygen_sukses_dan_roundtrip():
    async with await _client() as c:
        r = await c.post("/keygen", json={}, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()

    # public_key_pem valid + fingerprint cocok dengan key tersebut.
    pub = serialization.load_pem_public_key(body["public_key_pem"].encode("ascii"))
    assert re.fullmatch(r"[0-9a-f]{64}", body["public_key_fingerprint"])
    from app.crypto import keywrap, rsa

    assert rsa.public_key_fingerprint(pub) == body["public_key_fingerprint"]

    # Blob terenkripsi ter-decode base64 dan ter-dekrip kembali ke DER
    # yang pasangannya = public key di atas (roundtrip penyimpanan web).
    blob = base64.b64decode(body["encrypted_private_key_base64"])
    der = keywrap.decrypt_private_key(blob)
    priv = serialization.load_der_private_key(der, password=None)
    assert priv.key_size == 2048
    assert (
        rsa.public_key_fingerprint(priv.public_key())
        == body["public_key_fingerprint"]
    )


async def test_keygen_unik_per_panggilan():
    async with await _client() as c:
        a = (await c.post("/keygen", json={}, headers=HEADERS)).json()
        b = (await c.post("/keygen", json={}, headers=HEADERS)).json()
    assert a["public_key_fingerprint"] != b["public_key_fingerprint"]
    assert a["encrypted_private_key_base64"] != b["encrypted_private_key_base64"]
