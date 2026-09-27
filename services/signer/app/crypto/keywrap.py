"""Enkripsi private key at-rest (FR-03).

Alur wajib: ``RSA private key (DER)`` -> ``AES-256-GCM`` dengan key dari
``PRIVATE_KEY_ENCRYPTION_KEY`` (base64, tepat 32 byte) -> ``bytea``.
Nonce/IV 12 byte unik per operasi, disimpan sebagai prefix ciphertext:
``blob = nonce(12B) || ct``. Dekripsi HANYA di proses signer.
"""

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12
KEY_SIZE = 32


def get_encryption_key() -> bytes:
    """Baca + validasi PRIVATE_KEY_ENCRYPTION_KEY. Raise ValueError bila
    kosong/bukan base64/bukan 32 byte (fail-closed — jangan enkrip dengan
    key lemah)."""
    raw = os.environ.get("PRIVATE_KEY_ENCRYPTION_KEY", "")
    if not raw:
        raise ValueError("PRIVATE_KEY_ENCRYPTION_KEY belum diisi di environment")
    try:
        key = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("PRIVATE_KEY_ENCRYPTION_KEY bukan base64 valid") from exc
    if len(key) != KEY_SIZE:
        raise ValueError(
            f"PRIVATE_KEY_ENCRYPTION_KEY harus 32 byte, terbaca {len(key)} byte"
        )
    return key


def encrypt_private_key(private_der: bytes, key: bytes | None = None) -> bytes:
    """Enkripsi DER -> blob ``nonce || ciphertext`` untuk kolom bytea."""
    key = key if key is not None else get_encryption_key()
    nonce = os.urandom(NONCE_SIZE)
    ct = AESGCM(key).encrypt(nonce, private_der, associated_data=None)
    return nonce + ct


def decrypt_private_key(blob: bytes, key: bytes | None = None) -> bytes:
    """Dekripsi blob -> DER. Raise ValueError bila blob korup/tag invalid
    (jangan bocorkan detail kripto ke caller; pesan generik)."""
    key = key if key is not None else get_encryption_key()
    if len(blob) <= NONCE_SIZE:
        raise ValueError("Encrypted blob korup (terlalu pendek)")
    nonce, ct = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
    try:
        return AESGCM(key).decrypt(nonce, ct, associated_data=None)
    except InvalidTag as exc:
        raise ValueError("Dekripsi gagal (tag invalid / key salah)") from exc
