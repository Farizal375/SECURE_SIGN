"""Verifikasi PDF bertanda (pratinjau FR-09 penuh — B7 mengunci urutan).

B6: validasi via pyHanko (digest ByteRange + CMS) dengan trust root =
sertifikat ephemeral yang tertanam di CMS itu sendiri. Identitas signer
tetap mengacu public key tersimpan di sisi web (FR-09 langkah 5-6),
bukan sertifikat ini.

Return: dict(valid, integrity, signature_valid, public_key_fingerprint).
Fingerprint None bila tidak ada signature field sama sekali.
"""

import hashlib
from io import BytesIO

from pyhanko.pdf_utils.misc import PdfReadError
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import ValidationContext, validate_pdf_signature


def _spki_fingerprint(asn1_cert) -> str:
    """SHA256(SPKI DER) hex64 — konsisten dengan crypto.rsa (PRD §8)."""
    return hashlib.sha256(asn1_cert.public_key.dump()).hexdigest()


def verify_pdf_signature(pdf_bytes: bytes) -> dict:
    """Verifikasi signature terbaru di PDF. Raise PdfReadError bila bukan PDF."""
    if not pdf_bytes.startswith(b"%PDF-"):
        raise PdfReadError("bukan file PDF (magic bytes %PDF- tidak ada)")
    try:
        reader = PdfFileReader(BytesIO(pdf_bytes))
    except (PdfReadError, ValueError) as exc:
        raise PdfReadError(f"PDF tidak dapat diparse: {exc}") from exc

    try:
        sigs = list(reader.embedded_signatures)
    except Exception:
        # Struktur PDF terbaca, tapi daftar signature rusak (mis. /Contents
        # diutak-atik). Fail-closed: invalid, tetap HTTP 200.
        return {
            "valid": False,
            "integrity": False,
            "signature_valid": False,
            "public_key_fingerprint": None,
        }

    if not sigs:
        return {
            "valid": False,
            "integrity": False,
            "signature_valid": False,
            "public_key_fingerprint": None,
        }

    sig = sigs[-1]  # signature terbaru bila ada lebih dari satu
    trust_roots = []
    try:
        # Sertifikat penanda dari CMS (untuk trust + fingerprint).
        trust_roots = [sig.signer_cert] if sig.signer_cert is not None else []
    except (AttributeError, ValueError):
        trust_roots = []
    ctx = ValidationContext(trust_roots=trust_roots, allow_fetching=False)
    try:
        status = validate_pdf_signature(sig, signer_validation_context=ctx)
    except Exception:
        # CMS korup (mis. /Contents diutak-atik hingga tak ter-parse).
        # Fail-closed: laporkan invalid, TETAP HTTP 200 (FR-10/FR-12).
        return {
            "valid": False,
            "integrity": False,
            "signature_valid": False,
            "public_key_fingerprint": None,
        }

    fingerprint = None
    if status.signing_cert is not None:
        fingerprint = _spki_fingerprint(status.signing_cert)

    integrity = bool(status.intact)
    # FR-10: signature atas konten yang sudah di-tamper WAJIB false.
    # pyHanko memisahkan `valid` (keaslian CMS) dari `intact` (digest
    # ByteRange); signature_valid mensyaratkan keduanya.
    signature_valid = bool(status.valid and status.intact)
    return {
        "valid": bool(integrity and signature_valid),
        "integrity": integrity,
        "signature_valid": signature_valid,
        "public_key_fingerprint": fingerprint,
    }
