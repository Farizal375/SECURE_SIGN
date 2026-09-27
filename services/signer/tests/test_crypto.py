"""Test B2 — kripto mentah tanpa PDF (§14 langkah 6, AC-02/AC-03)."""

import base64
import os
import re

os.environ.setdefault("PRIVATE_KEY_ENCRYPTION_KEY", base64.b64encode(b"\x01" * 32).decode())

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.crypto import keywrap, rsa

DATA = b"digest-byterange-contoh-untuk-unit-test"


def test_ac02_key_rsa_2048():
    # AC-02: modulus tepat 2048 bit.
    priv = rsa.generate_rsa_keypair()
    assert priv.key_size == 2048
    assert priv.private_numbers().public_numbers.n.bit_length() == 2048
    assert priv.private_numbers().public_numbers.e == 65537


def test_fingerprint_format_spki():
    # PRD §8: SHA256(SPKI DER), hex lowercase 64 char; deterministik per key.
    priv = rsa.generate_rsa_keypair()
    fp = rsa.public_key_fingerprint(priv.public_key())
    assert re.fullmatch(r"[0-9a-f]{64}", fp)
    assert rsa.public_key_fingerprint(priv.public_key()) == fp
    assert rsa.public_key_fingerprint(rsa.generate_rsa_keypair().public_key()) != fp


def test_ac03_ciphertext_bukan_key_mentah():
    # AC-03: kolom encrypted_private_key tidak boleh ter-parse sebagai key.
    priv = rsa.generate_rsa_keypair()
    blob = keywrap.encrypt_private_key(rsa.private_key_to_der(priv))
    assert len(blob) > 12  # nonce 12B + ciphertext
    for loader in (
        serialization.load_pem_private_key,
        serialization.load_der_private_key,
    ):
        try:
            loader(blob, password=None)
        except ValueError:
            continue
        raise AssertionError("ciphertext ter-parse sebagai private key (BOCOR)")


def test_keywrap_roundtrip_dan_nonce_unik():
    priv = rsa.generate_rsa_keypair()
    der = rsa.private_key_to_der(priv)
    b1 = keywrap.encrypt_private_key(der)
    b2 = keywrap.encrypt_private_key(der)
    assert b1 != b2  # nonce unik per operasi (FR-03)
    assert keywrap.decrypt_private_key(b1) == der


def test_keywrap_key_salah_gagal():
    priv = rsa.generate_rsa_keypair()
    blob = keywrap.encrypt_private_key(rsa.private_key_to_der(priv))
    try:
        keywrap.decrypt_private_key(blob, key=b"\x02" * 32)
    except ValueError:
        return
    raise AssertionError("dekripsi dengan key salah seharusnya gagal")


def test_keywrap_blob_korup_gagal():
    try:
        keywrap.decrypt_private_key(b"pendek")
    except ValueError:
        return
    raise AssertionError("blob korup seharusnya gagal")


def test_get_encryption_key_validasi(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY_ENCRYPTION_KEY", "")
    try:
        keywrap.get_encryption_key()
    except ValueError:
        pass
    else:
        raise AssertionError("key kosong seharusnya raise")
    monkeypatch.setenv("PRIVATE_KEY_ENCRYPTION_KEY", "bukan-base64!!!")
    try:
        keywrap.get_encryption_key()
    except ValueError:
        pass
    else:
        raise AssertionError("key bukan base64 seharusnya raise")
    monkeypatch.setenv(
        "PRIVATE_KEY_ENCRYPTION_KEY", base64.b64encode(b"\x03" * 16).decode()
    )
    try:
        keywrap.get_encryption_key()
    except ValueError:
        pass
    else:
        raise AssertionError("key 16 byte seharusnya raise")


def test_pss_roundtrip():
    priv = rsa.generate_rsa_keypair()
    sig = rsa.pss_sign(priv, DATA)
    assert len(sig) == 256  # 2048 bit
    assert rsa.pss_verify(priv.public_key(), sig, DATA) is True


def test_pss_data_diubah_gagal():
    # Pratinjau FR-10: 1 byte berubah -> invalid.
    priv = rsa.generate_rsa_keypair()
    sig = rsa.pss_sign(priv, DATA)
    assert rsa.pss_verify(priv.public_key(), sig, DATA + b"\x00") is False


def test_pss_key_silang_gagal():
    # Pratinjau test tambahan §13: key B bukan pasangan -> INVALID.
    a = rsa.generate_rsa_keypair()
    b = rsa.generate_rsa_keypair()
    sig = rsa.pss_sign(a, DATA)
    assert rsa.pss_verify(b.public_key(), sig, DATA) is False


def test_pss_salt_32_bukan_max_length():
    # Bukti pipeline terkunci salt=32 (PRD §8 larang MAX_LENGTH):
    # signature salt-32 lolos verifier eksplisit salt-32, sedangkan
    # signature yang dibuat dengan MAX_LENGTH (salt 222) DITOLAK verifier kita.
    priv = rsa.generate_rsa_keypair()
    sig32 = rsa.pss_sign(priv, DATA)
    priv.public_key().verify(
        sig32, DATA,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )
    sig_max = priv.sign(
        DATA,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    assert rsa.pss_verify(priv.public_key(), sig_max, DATA) is False
