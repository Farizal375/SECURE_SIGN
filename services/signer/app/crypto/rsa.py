"""Operasi RSA (PRD §8 — parameter terkunci).

- Kunci: RSA 2048 bit, public exponent 65537.
- Signature: RSA-PSS, hash SHA-256, MGF1-SHA-256, salt length 32 byte
  (= digest size SHA-256). DILARANG memakai ``PSS.MAX_LENGTH`` (PRD §8).
- Fingerprint public key: ``SHA256(SPKI DER)``, hex lowercase 64 char.

Modul ini murni bytes-in/bytes-out, tidak tahu PDF/HTTP/DB.
DILARANG implementasi kripto sendiri (§2 aturan 2) — semua via ``cryptography``.
"""

import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

KEY_SIZE_BITS = 2048
PUBLIC_EXPONENT = 65537
PSS_SALT_LENGTH = 32  # = digest size SHA-256; DILARANG PSS.MAX_LENGTH


def generate_rsa_keypair() -> rsa.RSAPrivateKey:
    """Generate RSA-2048 key pair (FR-02)."""
    return rsa.generate_private_key(
        public_exponent=PUBLIC_EXPONENT,
        key_size=KEY_SIZE_BITS,
    )


def private_key_to_der(private_key: rsa.RSAPrivateKey) -> bytes:
    """Serialisasi private key ke DER (PKCS#8, tanpa enkripsi — enkripsi
    dilakukan terpisah oleh keywrap, FR-03)."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def public_key_to_pem(private_key: rsa.RSAPrivateKey) -> bytes:
    """Serialisasi public key ke PEM (SubjectPublicKeyInfo) untuk disimpan
    di ``signing_keys.public_key_pem``."""
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def public_key_fingerprint(public_key) -> str:
    """SHA256(SPKI DER), hex lowercase 64 char (PRD §8)."""
    spki_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(spki_der).hexdigest()


def _pss_padding() -> padding.PSS:
    return padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=PSS_SALT_LENGTH,
    )


def pss_sign(private_key: rsa.RSAPrivateKey, data: bytes) -> bytes:
    """RSA-PSS sign atas SHA-256(data). Dipakai untuk digest ByteRange (FR-08)."""
    return private_key.sign(data, _pss_padding(), hashes.SHA256())


def pss_verify(public_key, signature: bytes, data: bytes) -> bool:
    """Verifikasi RSA-PSS. True bila valid, False bila tidak (tak pernah raise
    untuk signature invalid — InvalidSignature ditelan jadi False)."""
    try:
        public_key.verify(signature, data, _pss_padding(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False
