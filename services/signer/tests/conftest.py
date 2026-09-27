"""Env default untuk seluruh test signer.

Test memakai secret/key dummy (TIDAK PERNAH secret produksi). Server
asli membaca services/signer/.env via load_dotenv (app/main.py).
"""

import base64
import os

os.environ.setdefault("SIGNER_SERVICE_SECRET", "test-secret-minimal-32-karakter-00")
os.environ.setdefault(
    "PRIVATE_KEY_ENCRYPTION_KEY", base64.b64encode(b"\x01" * 32).decode()
)
