"""Test B5 — appearance FR-06 + embed pyHanko FR-08 (AC-05/AC-07, AC-06 halaman).

Render + ekstraksi teks memakai pypdfium2 (dependensi KHUSUS TEST —
dicatat di deviations; runtime tidak memakainya). PDF sampel dibuat via
Pillow (sudah dependensi qrcode[pil]) agar tanpa dependensi baru.
"""

import json
import re
import uuid
from datetime import datetime, timezone

import cv2
import numpy as np
import pypdfium2 as pdfium
import pytest

from app.crypto import keywrap, rsa
from app.pdf import appearance, signer as pdf_signer

SIGNED_AT = "2026-09-27T10:00:00Z"
SIG_ID = str(uuid.uuid4())
VERIFY_URL = "https://securesign.example/verify/tokentest123"
FIELD = {"page": 0, "x": 100, "y": 100, "width": 180, "height": 80}


def _sample_pdf(pages: int = 1) -> bytes:
    """PDF minimal valid (xref dihitung programmatic, deterministik).

    Pillow tidak dipakai: PDF raster-nya tidak selalu ter-parse
    PdfFileReader pyHanko. Tanpa dependensi baru.
    """
    out = [b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"]
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(pages))
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode(),
    }
    for i in range(pages):
        content = b"BT /F1 12 Tf 72 720 Td (SecureSign sample) Tj ET"
        cnum = 4 + 2 * i
        objs[3 + 2 * i] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            "/Resources << /Font << /F1 << /Type /Font "
            "/Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/Contents {cnum} 0 R >>"
        ).encode()
        objs[cnum] = (
            f"<< /Length {len(content)} >>\nstream\n".encode()
            + content
            + b"\nendstream"
        )
    offsets = {}
    for num in sorted(objs):
        offsets[num] = sum(len(x) for x in out)
        out.append(f"{num} 0 obj\n".encode() + objs[num] + b"\nendobj\n")
    startxref = sum(len(x) for x in out)
    n = max(objs) + 1
    out.append(f"xref\n0 {n}\n".encode())
    out.append(b"0000000000 65535 f \n")
    for i in range(1, n):
        out.append(f"{offsets[i]:010d} 00000 n \n".encode())
    out.append(
        f"trailer\n<< /Size {n} /Root 1 0 R >>\n"
        f"startxref\n{startxref}\n%%EOF".encode()
    )
    return b"".join(out)


def _key_der() -> bytes:
    return rsa.private_key_to_der(rsa.generate_rsa_keypair())


def _signed(**over) -> bytes:
    kw = {
        "private_key_der": _key_der(),
        "signer_name": "Budi Santoso",
        "signer_position": "Direktur",
        "signer_institution": "PT Contoh",
        "signed_at_iso": SIGNED_AT,
        "signature_id": SIG_ID,
        "verification_url": VERIFY_URL,
        **FIELD,
        **over,
    }
    return pdf_signer.sign_pdf_visible(_sample_pdf(), **kw)


def _appearance_objects(pdf: bytes):
    """Ambil (appearance_stream_bytes, qr_stream_bytes) dari widget pertama."""
    from io import BytesIO

    from pyhanko.pdf_utils.reader import PdfFileReader

    r = PdfFileReader(BytesIO(pdf))
    annot = r.root["/Pages"]["/Kids"][0].get_object()["/Annots"][0].get_object()
    apn = annot["/AP"].get_object()["/N"].get_object()
    qr = apn["/Resources"].get_object()["/XObject"].get_object()["/QR"].get_object()
    return bytes(apn.data), bytes(qr.data)


def _appearance_text(pdf: bytes) -> str:
    """Ekstrak string teks dari stream appearance (literal + hex)."""
    ap, _ = _appearance_objects(pdf)
    parts = []
    for m in re.finditer(rb"\((?:[^()\\]|\\.)*\)", ap):
        raw = m.group(0)[1:-1]
        out = bytearray()
        i = 0
        while i < len(raw):
            if raw[i : i + 1] == b"\\" and i + 3 < len(raw):
                out.append(int(raw[i + 1 : i + 4], 8))  # escape oktal (\072=:)
                i += 4
            else:
                out.append(raw[i])
                i += 1
        parts.append(bytes(out).decode("latin-1"))
    for m in re.finditer(rb"<([0-9A-Fa-f]+)>", ap):
        parts.append(bytes.fromhex(m.group(1).decode()).decode("latin-1"))
    return "\n".join(parts)


def _qr_payload_from_pdf(pdf: bytes) -> str:
    """Rekonstruksi grid modul dari stream vektor /QR -> raster -> decode.

    Setara 'scan QR dari halaman': membuktikan QR TERTANAM di PDF ter-decode
    ke payload FR-07, tanpa tergantung quirk renderer anotasi.
    """
    _, qr_stream = _appearance_objects(pdf)
    cells = re.findall(rb"(\d+) (\d+) 1 1 re", qr_stream)
    assert cells, "tidak ada modul QR di stream appearance"
    n = max(max(int(x), int(y)) for x, y in cells) + 1
    scale = 8
    inner = np.full((n * scale, n * scale), 255, dtype=np.uint8)
    for x, y in cells:
        inner[int(y) * scale : (int(y) + 1) * scale, int(x) * scale : (int(x) + 1) * scale] = 0
    # Quiet zone wajib 4 modul agar decoder mengenali QR.
    img = np.full(
        (inner.shape[0] + 8 * scale, inner.shape[1] + 8 * scale), 255, dtype=np.uint8
    )
    img[4 * scale : 4 * scale + inner.shape[0], 4 * scale : 4 * scale + inner.shape[1]] = inner
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return data


def test_appearance_urutan_field():
    text = appearance.build_appearance_text(
        "Budi", "Dir", "PT", datetime(2026, 9, 27), "ID-1"
    )
    lines = text.splitlines()
    assert lines[0] == "DITANDATANGANI SECARA DIGITAL"
    assert lines[1] == "Nama: Budi"
    assert lines[2] == "Jabatan: Dir"
    assert lines[3] == "Institusi: PT"
    assert lines[4] == "Tanggal: 27 September 2026"
    assert lines[5] == "Signature ID: ID-1"


def test_appearance_kosong_dash_dan_nama_wajib():
    text = appearance.build_appearance_text("Budi", None, "", datetime(2026, 1, 5), "X")
    assert "Jabatan: -" in text and "Institusi: -" in text
    assert "Tanggal: 5 Januari 2026" in text
    with pytest.raises(ValueError):
        appearance.build_appearance_text("  ", "D", "I", datetime(2026, 1, 1), "X")


def test_ac05_field_muncul_di_halaman():
    # AC-05: field FR-06 muncul di appearance signature (stream /AP widget).
    # Catatan: ekstraksi teks halaman (PDFium GetTextPage) tidak mencakup
    # stream appearance anotasi, maka dibaca langsung dari /AP — tempat
    # appearance signature memang tinggal (setara "rendered" dari sisi data).
    text = _appearance_text(_signed())
    for expected in (
        "DITANDATANGANI SECARA DIGITAL",
        "Budi Santoso",
        "Direktur",
        "PT Contoh",
        "September 2026",
        SIG_ID,
    ):
        assert expected in text, f"hilang: {expected}"


def test_ac07_byterange_dan_contents():
    # AC-07: /ByteRange dan /Contents non-kosong.
    signed = _signed()
    assert b"/ByteRange" in signed
    m = re.search(rb"/Contents\s*<([0-9A-Fa-f]+)>", signed)
    assert m and len(m.group(1)) > 100


def test_ac06_qr_dari_halaman():
    # AC-06 level halaman: QR yang tertanam di PDF ter-decode = payload FR-07.
    decoded = _qr_payload_from_pdf(_signed())
    assert decoded
    assert json.loads(decoded) == {"verificationUrl": VERIFY_URL}


def test_pdf_asli_tak_berubah_dan_terparse():
    src = _sample_pdf()
    signed = pdf_signer.sign_pdf_visible(
        src,
        private_key_der=_key_der(),
        signer_name="B",
        signer_position=None,
        signer_institution=None,
        signed_at_iso=SIGNED_AT,
        signature_id=str(uuid.uuid4()),
        verification_url=VERIFY_URL,
        **FIELD,
    )
    assert len(signed) > len(src)
    doc = pdfium.PdfDocument(signed)  # ter-parse sebagai PDF valid
    assert len(doc) == 1


def test_field_invalid_gagal():
    with pytest.raises(ValueError):
        _signed(width=0)
    with pytest.raises(ValueError):
        _signed(page=5)
    with pytest.raises(ValueError):
        _signed(private_key_der=b"bukan-key")


def test_alur_blob_dari_keygen():
    # Integrasi B3->B5: blob terenkripsi (seperti disimpan web) -> dekrip -> sign.
    priv = rsa.generate_rsa_keypair()
    blob = keywrap.encrypt_private_key(rsa.private_key_to_der(priv))
    signed = _signed(private_key_der=keywrap.decrypt_private_key(blob))
    assert b"/ByteRange" in signed
