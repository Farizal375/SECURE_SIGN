"""Test B7 — verifikasi penuh FR-09/10/11 + pratinjau FR-12 (AC-08 s.d. AC-11).

Batasan kepemilikan (PRD): lookup token di `verification_records`
(FR-12/AC-11) adalah lapis WEB (butuh DB via Prisma). Yang diuji di sini:
- AC-08: PDF asli VALID (semua boolean true, independen).
- AC-09/FR-10: 1 byte diubah di luar /Contents -> integrity+signature_valid
  false, HTTP TETAP 200.
- Varian: byte diubah di DALAM /Contents -> valid false, 200.
- AC-10/FR-11: kunci silang -> fingerprint beda sehingga lapisan web
  mendeteksi publicKeyMatch=false (simulasi perbandingan web di test).
- Binding token: QR di PDF ter-decode ke verification_url yang dikirim
  (prasyarat FR-12 di sisi web: token tak terdaftar -> tokenValid false).
"""

import base64
import json
import os
import re
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.crypto import keywrap, rsa
from app.main import app
from app.security import auth
from test_pdf import _qr_payload_from_pdf, _sample_pdf

pytestmark = pytest.mark.anyio

HEADERS = {auth.HEADER_NAME: os.environ["SIGNER_SERVICE_SECRET"]}


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _keypair():
    priv = rsa.generate_rsa_keypair()
    blob = base64.b64encode(
        keywrap.encrypt_private_key(rsa.private_key_to_der(priv))
    ).decode()
    return priv, blob


def _body(doc_b64, blob_b64, url, sig_id=None):
    return {
        "document_base64": doc_b64,
        "key_id": str(uuid.uuid4()),
        "encrypted_private_key_base64": blob_b64,
        "signature_field": {"page": 0, "x": 100, "y": 100, "width": 180, "height": 80},
        "signer_name": "Budi Santoso",
        "signer_position": "Direktur",
        "signer_institution": "PT Contoh",
        "signed_at": "2026-09-27T10:00:00Z",
        "verification_url": url,
        "signature_id": sig_id or str(uuid.uuid4()),
    }


async def _sign(blob_b64, url):
    doc_b64 = base64.b64encode(_sample_pdf()).decode()
    async with await _client() as c:
        r = await c.post("/sign", json=_body(doc_b64, blob_b64, url), headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


async def _verify(doc_b64):
    async with await _client() as c:
        r = await c.post("/verify", json={"document_base64": doc_b64}, headers=HEADERS)
    return r.status_code, r.json()


def _tamper_luar_contents(signed: bytes) -> bytes:
    """Ubah 1 byte di dalam range ByteRange pertama (area header %PDF)."""
    m = re.search(rb"/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]", signed)
    assert m, "ByteRange tidak ditemukan"
    off = int(m.group(1)) + 10
    assert off < int(m.group(1)) + int(m.group(2)), "offset di luar coverage"
    buf = bytearray(signed)
    buf[off] ^= 0x01
    return bytes(buf)


def _tamper_dalam_contents(signed: bytes) -> bytes:
    """Ubah 1 digit hex di dalam /Contents (tetap hex valid agar ter-parse)."""
    m = re.search(rb"/Contents\s*<([0-9A-Fa-f]+)>", signed)
    assert m, "Contents tidak ditemukan"
    start, end = m.span(1)
    buf = bytearray(signed)
    orig = buf[start : start + 1].decode()
    buf[start : start + 1] = b"B" if orig != "B" else b"C"
    assert end - start > 100
    return bytes(buf)


async def test_ac08_pdf_asli_valid_independen():
    # AC-08 + FR-09: semua boolean true dan dilaporkan independen.
    _, blob = _keypair()
    signed = await _sign(blob, "https://securesign.example/verify/ac08")
    st, body = await _verify(signed["signed_document_base64"])
    assert st == 200
    assert body["valid"] is True
    assert body["integrity"] is True
    assert body["signature_valid"] is True
    assert body["public_key_fingerprint"] == signed["public_key_fingerprint"]


async def test_ac09_tamper_1byte_luar_contents():
    # FR-10/AC-09: HTTP tetap 200, integrity+signature_valid false.
    _, blob = _keypair()
    signed = await _sign(blob, "https://securesign.example/verify/ac09")
    raw = base64.b64decode(signed["signed_document_base64"])
    tampered = base64.b64encode(_tamper_luar_contents(raw)).decode()
    st, body = await _verify(tampered)
    assert st == 200, "tamper WAJIB tetap HTTP 200 (bukan 4xx)"
    assert body["valid"] is False
    assert body["integrity"] is False
    assert body["signature_valid"] is False


async def test_tamper_dalam_contents_invalid():
    _, blob = _keypair()
    signed = await _sign(blob, "https://securesign.example/verify/ac09b")
    raw = base64.b64decode(signed["signed_document_base64"])
    tampered = base64.b64encode(_tamper_dalam_contents(raw)).decode()
    st, body = await _verify(tampered)
    assert st == 200
    assert body["valid"] is False


async def test_ac10_wrong_key_terdeteksi_web():
    # FR-11: signer mengembalikan fingerprint apa adanya; WEB yang
    # membandingkan dengan fingerprint tersimpan -> publicKeyMatch.
    # Di sini dibuktikan kedua sisi: fingerprint A != B sehingga
    # perbandingan web pasti false.
    priv_a, blob_a = _keypair()
    _, blob_b = _keypair()
    fp_a = rsa.public_key_fingerprint(priv_a.public_key())
    s = await _sign(blob_a, "https://securesign.example/verify/ac10")
    assert s["public_key_fingerprint"] == fp_a  # kasus cocok
    st, body = await _verify(s["signed_document_base64"])
    assert st == 200 and body["signature_valid"] is True
    # Simulasi web menyimpan fp_B tapi menerima fp_A:
    s_b = await _sign(blob_b, "https://securesign.example/verify/ac10b")
    public_key_match = s["public_key_fingerprint"] == s_b["public_key_fingerprint"]
    assert public_key_match is False, "kunci silang harus terdeteksi mismatch"


async def test_qr_binding_per_url():
    # Prasyarat FR-12: tiap URL verifikasi terikat ke QR-nya masing-masing.
    _, blob = _keypair()
    urls = [
        "https://securesign.example/verify/token-pertama",
        "https://securesign.example/verify/token-kedua",
    ]
    for url in urls:
        s = await _sign(blob, url)
        raw = base64.b64decode(s["signed_document_base64"])
        assert json.loads(_qr_payload_from_pdf(raw)) == {"verificationUrl": url}
