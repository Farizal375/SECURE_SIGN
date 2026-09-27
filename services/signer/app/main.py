"""SecureSign Signing Service — entrypoint (PRD §4.1, §9, §15).

Urutan middleware (request flow): RequestLogging -> Auth -> router,
sehingga 401 dari Auth tetap tercatat sebagai JSON + ber-X-Request-ID.
Starlette menjalankan middleware yang terakhir didaftarkan paling luar,
maka Auth didaftar dulu, Logging sesudahnya.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.keygen import router as keygen_router
from app.api.sign import router as sign_router
from app.api.verify import router as verify_router
from app.security.auth import AuthMiddleware
from app.security.logging import RequestLoggingMiddleware, configure_logging, log_event

load_dotenv()
logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail-closed saat boot: secret kosong -> service menolak start (PRD §9).
    if not os.environ.get("SIGNER_SERVICE_SECRET", ""):
        logger.critical("SIGNER_SERVICE_SECRET kosong — service menolak start (fail-closed, PRD §9)")
        raise RuntimeError("SIGNER_SERVICE_SECRET belum diisi di environment")
    log_event(logger, "startup", status="ready")
    yield
    log_event(logger, "shutdown")


app = FastAPI(
    title="SecureSign Signer Service",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(keygen_router)
app.include_router(sign_router)
app.include_router(verify_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
