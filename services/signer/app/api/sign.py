"""POST /sign — endpoint internal (keputusan terkunci #1 + #4).

Request = skema PRD §11 + 7 field (lihat rencana B6 yang dikunci):
document_base64, key_id, encrypted_private_key_base64, signature_field,
signer_name, signer_position, signer_institution, signed_at,
verification_url, signature_id.

- ``key_id`` hanya echo/korelasi (signer stateless, tidak query DB);
  format UUID divalidasi.
- ``page`` 0-based; ``y`` dari ATAS (dikonversi di pdf/signer.py).
- Extra field DITOLAK (fail-closed: drift kontrak langsung 422).
"""

import base64
import binascii
import functools
import logging
import uuid

import anyio
from cryptography.hazmat.primitives.serialization import load_der_private_key
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from pyhanko.pdf_utils.misc import PdfReadError

from app.crypto import keywrap, rsa
from app.pdf import signer as pdf_signer
from app.security.logging import bind_context, log_event

logger = logging.getLogger("signer")
router = APIRouter()


class SignatureField(BaseModel):
    page: int = Field(ge=0)
    x: float
    y: float
    width: float
    height: float


class SignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_base64: str
    key_id: str
    encrypted_private_key_base64: str
    signature_field: SignatureField
    signer_name: str
    signer_position: str | None = None
    signer_institution: str | None = None
    signed_at: str
    verification_url: str
    signature_id: str


class SignResponse(BaseModel):
    signed_document_base64: str
    signature_algorithm: str
    hash_algorithm: str
    public_key_fingerprint: str


def _invalid(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "INVALID_REQUEST", "message": message}},
    )


@router.post("/sign", response_model=SignResponse)
async def sign(req: SignRequest):
    try:
        key_uuid = str(uuid.UUID(req.key_id))
    except ValueError:
        return _invalid("key_id bukan UUID valid")
    try:
        document = base64.b64decode(req.document_base64, validate=True)
    except (binascii.Error, ValueError):
        return _invalid("document_base64 bukan base64 valid")
    try:
        blob = base64.b64decode(req.encrypted_private_key_base64, validate=True)
    except (binascii.Error, ValueError):
        return _invalid("encrypted_private_key_base64 bukan base64 valid")
    try:
        private_der = keywrap.decrypt_private_key(blob)
    except ValueError as exc:
        return _invalid(f"encrypted_private_key invalid: {exc}")

    bind_context(keyId=key_uuid, signatureId=req.signature_id)
    try:
        fingerprint = rsa.public_key_fingerprint(
            load_der_private_key(private_der, password=None).public_key()
        )
        # CPU-bound + pyHanko memanggil asyncio.run() di dalamnya: JANGAN
        # dieksekusi di event loop (blocking + nested-loop error). Lempar ke
        # worker thread; fungsi sync-nya tetap sama untuk pemakaian langsung.
        signed = await anyio.to_thread.run_sync(
            functools.partial(
                pdf_signer.sign_pdf_visible,
                document,
                private_key_der=private_der,
                signer_name=req.signer_name,
                signer_position=req.signer_position,
                signer_institution=req.signer_institution,
                signed_at_iso=req.signed_at,
                signature_id=req.signature_id,
                verification_url=req.verification_url,
                page=req.signature_field.page,
                x=req.signature_field.x,
                y=req.signature_field.y,
                width=req.signature_field.width,
                height=req.signature_field.height,
            )
        )
    except (ValueError, PdfReadError) as exc:
        log_event(logger, "sign", status="failed")
        return _invalid(str(exc))

    log_event(logger, "sign", status="success")
    return SignResponse(
        signed_document_base64=base64.b64encode(signed).decode("ascii"),
        signature_algorithm="RSA-PSS",
        hash_algorithm="SHA-256",
        public_key_fingerprint=fingerprint,
    )
