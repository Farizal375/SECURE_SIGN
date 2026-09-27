"""POST /verify — endpoint internal, skema persis PRD §11.

Request: ``{ "document_base64": "..." }``.
Response 200: ``{valid, integrity, signature_valid, public_key_fingerprint}``.
``public_key_fingerprint`` = null bila tidak ada signature field.

PDF tak ter-parse / base64 invalid -> 422 INVALID_REQUEST.
"""

import base64
import binascii
import functools
import logging

import anyio
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pyhanko.pdf_utils.misc import PdfReadError

from app.security.logging import bind_context, log_event
from app.verification import verify as verify_mod

logger = logging.getLogger("signer")
router = APIRouter()


class VerifyRequest(BaseModel):
    document_base64: str


class VerifyResponse(BaseModel):
    valid: bool
    integrity: bool
    signature_valid: bool
    public_key_fingerprint: str | None


@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest):
    try:
        document = base64.b64decode(req.document_base64, validate=True)
    except (binascii.Error, ValueError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "document_base64 bukan base64 valid",
                }
            },
        )
    try:
        # CPU-bound (hash + RSA). Jalan di worker thread agar tak block loop.
        result = await anyio.to_thread.run_sync(
            functools.partial(verify_mod.verify_pdf_signature, document)
        )
    except PdfReadError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_REQUEST", "message": str(exc)}},
        )
    bind_context()
    log_event(
        logger,
        "verify",
        status="success" if result["valid"] else "invalid",
    )
    return VerifyResponse(**result)
