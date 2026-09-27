"""Endpoint internal signer (keputusan terkunci #2, dicatat di deviations).

POST /keygen — generate RSA-2048 + enkripsi AES-256-GCM, kembalikan public
key + fingerprint + blob terenkripsi agar web menyimpannya ke
``signing_keys``. Private key plaintext TIDAK PERNAH transit (hanya blob).
Header §9 wajib (ditegakkan middleware, bukan di sini).
"""

import base64

from fastapi import APIRouter
from pydantic import BaseModel

from app.crypto import keywrap, rsa

router = APIRouter()


class KeygenResponse(BaseModel):
    public_key_pem: str
    public_key_fingerprint: str
    encrypted_private_key_base64: str


@router.post("/keygen", response_model=KeygenResponse)
async def keygen() -> KeygenResponse:
    private_key = rsa.generate_rsa_keypair()
    der = rsa.private_key_to_der(private_key)
    blob = keywrap.encrypt_private_key(der)
    pem = rsa.public_key_to_pem(private_key).decode("ascii")
    return KeygenResponse(
        public_key_pem=pem,
        public_key_fingerprint=rsa.public_key_fingerprint(private_key.public_key()),
        encrypted_private_key_base64=base64.b64encode(blob).decode("ascii"),
    )
