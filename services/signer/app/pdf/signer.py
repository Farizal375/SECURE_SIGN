"""Embed signature visible ke PDF via pyHanko (FR-08).

DILARANG membangun struktur /AcroForm /Sig /ByteRange /Contents manual —
seluruh container CMS/PKCS#7 detached dibuat pyHanko.

Kontrak koordinat (DIKUNCI, wajib disepakati frontend):
- ``page`` 0-based (PRD §11), ``x/y/width/height`` dalam point PDF.
- ``x`` = jarak dari KIRI, ``y`` = jarak dari ATAS (konvensi PDF.js/react-pdf
  yang dipakai preview FR-05). Dikonversi ke origin kiri-bawah PDF:
  ``y_bottom = page_height - y - height``.
- Rotasi halaman diabaikan (MVP); halaman ter-rotasi /CropBox non-standar
  di luar cakupan — dicatat di deviations bila ditemui.

Sertifikat: CMS butuh sertifikat X.509. Sertifikat dibuat EPHEMERAL
(self-signed, CN = nama signer, 10 tahun) dari RSA key setiap panggilan —
tidak disimpan di mana pun. Verifikasi identitas mengacu public key
tersimpan (FR-09 langkah 5-6), bukan sertifikat ini.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko.sign.fields import SigFieldSpec
from pyhanko.stamp import QRStampStyle, QRPosition

from app.pdf.appearance import build_appearance_text, parse_signed_at
from app.qr.generator import build_qr_payload


def make_ephemeral_cert(private_key: rsa.RSAPrivateKey, common_name: str) -> bytes:
    """Self-signed cert DER ephemeral untuk container CMS."""
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    from cryptography.hazmat.primitives.serialization import Encoding

    return cert.public_bytes(Encoding.DER)


def _page_height(pdf_bytes: bytes, page_index: int) -> float:
    reader = PdfFileReader(BytesIO(pdf_bytes))
    n_pages = len(reader.root["/Pages"]["/Kids"])
    if not (0 <= page_index < n_pages):
        raise ValueError(f"page {page_index} di luar jumlah halaman ({n_pages})")
    mediabox = reader.root["/Pages"]["/Kids"][page_index].get_object()["/MediaBox"]
    return float(mediabox[3]) - float(mediabox[1])


def sign_pdf_visible(
    pdf_bytes: bytes,
    *,
    private_key_der: bytes,
    signer_name: str,
    signer_position: str | None,
    signer_institution: str | None,
    signed_at_iso: str,
    signature_id: str,
    verification_url: str,
    page: int,
    x: float,
    y: float,
    width: float,
    height: float,
) -> bytes:
    """Tandatangani PDF: appearance (teks FR-06 + QR FR-07) + embed /Sig.

    Return: bytes PDF bertanda (incremental update, PDF asli tak diubah).
    Raise ValueError untuk input invalid (fail-closed).
    """
    if width <= 0 or height <= 0:
        raise ValueError("width/height harus > 0 (FR-05)")
    from cryptography.hazmat.primitives.serialization import load_der_private_key

    try:
        private_key = load_der_private_key(private_key_der, password=None)
    except (ValueError, TypeError) as exc:
        raise ValueError("private_key_der invalid") from exc
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("key harus RSA")

    signed_at = parse_signed_at(signed_at_iso)
    text = build_appearance_text(
        signer_name, signer_position, signer_institution, signed_at, signature_id
    )
    qr_payload = build_qr_payload(verification_url)

    page_h = _page_height(pdf_bytes, page)
    y_bottom = page_h - y - height
    if y_bottom < 0:
        raise ValueError("kotak signature di luar halaman (y melebihi tinggi)")

    style = QRStampStyle(
        stamp_text=text,
        qr_position=QRPosition.LEFT_OF_TEXT,
    )
    field_name = f"SecureSign_{signature_id}"
    spec = SigFieldSpec(
        sig_field_name=field_name,
        on_page=page,
        box=(x, y_bottom, x + width, y_bottom + height),
    )
    meta = signers.PdfSignatureMetadata(field_name=field_name, md_algorithm="sha256")

    cert_der = make_ephemeral_cert(private_key, signer_name.strip())
    # Konstruksi SimpleSigner langsung dari bytes (tanpa file temp agar
    # private key plaintext tidak pernah menyentuh disk — FR-02).
    from asn1crypto import keys as asn1_keys
    from asn1crypto import x509 as asn1_x509
    from pyhanko_certvalidator.registry import SimpleCertificateStore

    asn1_cert = asn1_x509.Certificate.load(cert_der)
    asn1_key = asn1_keys.PrivateKeyInfo.load(private_key_der)
    signer = signers.SimpleSigner(
        signing_cert=asn1_cert,
        signing_key=asn1_key,
        cert_registry=SimpleCertificateStore(),
        prefer_pss=True,
    )

    writer = IncrementalPdfFileWriter(BytesIO(pdf_bytes))
    out = BytesIO()
    signers.PdfSigner(
        meta, signer, stamp_style=style, new_field_spec=spec
    ).sign_pdf(
        writer,
        appearance_text_params={"url": qr_payload},
        output=out,
    )
    return out.getvalue()
