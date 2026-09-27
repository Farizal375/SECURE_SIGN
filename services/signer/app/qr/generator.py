"""QR-Code verifikasi (FR-07).

Payload QR HANYA ``{"verificationUrl": "https://<domain>/verify/<token>"}}``.
DILARANG field lain. Token plaintext hanya ada di URL ini, tidak disimpan.

Catatan parameter (PRD tidak mengunci detail render QR; dipilih fail-closed):
- Error correction M: tahan kerusakan sebagian namun tidak boros modul.
- box_size=10, border=4: memenuhi quiet zone standar agar mudah di-scan
  setelah dokumen di-print/screenshot.
"""

import io
import json

import qrcode
from qrcode.constants import ERROR_CORRECT_M

QR_PAYLOAD_KEY = "verificationUrl"


def build_qr_payload(verification_url: str) -> str:
    """Bangun string payload JSON. Raise ValueError bila URL kosong."""
    if not verification_url or not verification_url.strip():
        raise ValueError("verification_url wajib diisi (tidak boleh kosong)")
    return json.dumps({QR_PAYLOAD_KEY: verification_url})


def generate_qr_png(verification_url: str) -> bytes:
    """Render payload FR-07 menjadi PNG bytes (siap ditempel ke PDF)."""
    payload = build_qr_payload(verification_url)
    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
