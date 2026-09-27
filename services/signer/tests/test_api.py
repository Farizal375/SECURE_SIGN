"""Test B6 — POST /sign + POST /verify end-to-end (ASGI, tanpa server)."""

import base64
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.crypto import keywrap, rsa
from app.main import app
from app.security import auth
from test_pdf import _sample_pdf

pytestmark = pytest.mark.anyio

HEADERS = {auth.HEADER_NAME: os.environ["SIGNER_SERVICE_SECRET"]}
SIG_ID = str(uuid.uuid4())


def _key_material():
    priv = rsa.generate_rsa_keypair()
    der = rsa.private_key_to_der(priv)
    blob = keywrap.encrypt_private_key(der)
    return priv, base64.b64encode(blob).decode("ascii")


def _sign_body(doc_b64, blob_b64, **over):
    body = {
        "document_base64": doc_b64,
        "key_id": str(uuid.uuid4()),
        "encrypted_private_key_base64": blob_b64,
        "signature_field": {"page": 0, "x": 100, "y": 100, "width": 180, "height": 80},
        "signer_name": "Budi Santoso",
        "signer_position": "Direktur",
        "signer_institution": "PT Contoh",
        "signed_at": "2026-09-27T10:00:00Z",
        "verification_url": "https://securesign.example/verify/tok123",
        "signature_id": SIG_ID,
    }
    body.update(over)
    return body


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _signed_b64():
    _, blob_b64 = _key_material()
    doc_b64 = base64.b64encode(_sample_pdf()).decode("ascii")
    async with await _client() as c:
        r = await c.post("/sign", json=_sign_body(doc_b64, blob_b64), headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


async def test_sign_tanpa_header_401():
    async with await _client() as c:
        r = await c.post("/sign", json={})
    assert r.status_code == 401


async def test_sign_full_flow_200():
    priv, blob_b64 = _key_material()
    expected_fp = rsa.public_key_fingerprint(priv.public_key())
    doc_b64 = base64.b64encode(_sample_pdf()).decode("ascii")
    async with await _client() as c:
        r = await c.post("/sign", json=_sign_body(doc_b64, blob_b64), headers=HEADERS)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["signature_algorithm"] == "RSA-PSS"
    assert body["hash_algorithm"] == "SHA-256"
    assert body["public_key_fingerprint"] == expected_fp
    signed = base64.b64decode(body["signed_document_base64"])
    assert b"/ByteRange" in signed and b"/Contents" in signed


async def test_sign_input_invalid_422():
    _, blob_b64 = _key_material()
    doc_b64 = base64.b64encode(_sample_pdf()).decode("ascii")
    cases = [
        _sign_body("bukan-base64!!!", blob_b64),  # dokumen korup
        _sign_body(doc_b64, "bukan-base64!!!"),  # blob korup
        _sign_body(doc_b64, blob_b64, key_id="bukan-uuid"),  # key_id
        _sign_body(doc_b64, blob_b64, width=0),  # field tak dikenal -> forbid? (diabaikan)
    ]
    async with await _client() as c:
        for body in cases[:3]:
            r = await c.post("/sign", json=body, headers=HEADERS)
            assert r.status_code == 422, body
            assert r.json()["error"]["code"] == "INVALID_REQUEST"
        # Extra field di root DITOLAK (extra=forbid).
        body = _sign_body(doc_b64, blob_b64)
        body["field_tak_dikenal"] = 1
        r = await c.post("/sign", json=body, headers=HEADERS)
        assert r.status_code == 422


async def test_verify_signed_semua_true():
    signed = await _signed_b64()
    async with await _client() as c:
        r = await c.post(
            "/verify",
            json={"document_base64": signed["signed_document_base64"]},
            headers=HEADERS,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] is True
    assert body["integrity"] is True
    assert body["signature_valid"] is True
    assert body["public_key_fingerprint"] == signed["public_key_fingerprint"]


async def test_verify_tanpa_signature_semua_false():
    doc_b64 = base64.b64encode(_sample_pdf()).decode("ascii")
    async with await _client() as c:
        r = await c.post("/verify", json={"document_base64": doc_b64}, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "valid": False,
        "integrity": False,
        "signature_valid": False,
        "public_key_fingerprint": None,
    }


async def test_verify_input_invalid_422():
    async with await _client() as c:
        r = await c.post("/verify", json={"document_base64": "!!!"}, headers=HEADERS)
        assert r.status_code == 422
        not_pdf = base64.b64encode(b"bukan pdf sama sekali").decode("ascii")
        r = await c.post("/verify", json={"document_base64": not_pdf}, headers=HEADERS)
        assert r.status_code == 422


async def test_verify_tanpa_header_401():
    async with await _client() as c:
        r = await c.post("/verify", json={"document_base64": "eA=="})
    assert r.status_code == 401
