"""Test B4 — QR-Code (FR-07, pratinjau AC-06).

Decode memakai cv2 (opencv-python-headless, dependensi KHUSUS TEST —
dicatat di docs/deviations.md; runtime signer tidak memakainya).
"""

import io
import json

import cv2
import numpy as np
import pytest
from PIL import Image

from app.qr import generator

URL = "https://securesign.example/verify/abcDEF123-_xyz"


def _decode(png: bytes) -> str:
    img = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    assert img is not None
    # Quiet zone: decoder butuh margin putih di sekeliling QR.
    pad = 40
    canvas = np.full(
        (img.shape[0] + 2 * pad, img.shape[1] + 2 * pad), 255, dtype=np.uint8
    )
    canvas[pad : pad + img.shape[0], pad : pad + img.shape[1]] = img
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(canvas)
    return data


def test_payload_hanya_verification_url():
    payload = generator.build_qr_payload(URL)
    obj = json.loads(payload)
    assert set(obj.keys()) == {"verificationUrl"}  # FR-07: DILARANG field lain
    assert obj["verificationUrl"] == URL


def test_payload_url_kosong_gagal():
    for bad in ("", "   "):
        with pytest.raises(ValueError):
            generator.build_qr_payload(bad)
    with pytest.raises(ValueError):
        generator.generate_qr_png("")


def test_ac06_qr_terdecode_persis_url():
    # AC-06 (level PNG; level PDF halaman penuh menyusul di B5/AC).
    png = generator.generate_qr_png(URL)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    Image.open(io.BytesIO(png)).verify()  # PNG valid
    decoded = _decode(png)
    assert decoded  # terdeteksi sebagai QR
    obj = json.loads(decoded)
    assert obj == {"verificationUrl": URL}


def test_qr_token_acak_terdecode():
    # Token 32 byte base64url realistis (dibuat web, bukan signer).
    import secrets

    token = secrets.token_urlsafe(32)
    url = f"https://securesign.example/verify/{token}"
    decoded = _decode(generator.generate_qr_png(url))
    assert json.loads(decoded)["verificationUrl"] == url
