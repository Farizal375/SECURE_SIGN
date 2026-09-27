"""Appearance tanda tangan visible (FR-06).

Urutan field WAJIB (atas ke bawah):
  1. judul "DITANDATANGANI SECARA DIGITAL"
  2. Nama        <- profiles.full_name
  3. Jabatan     <- profiles.position
  4. Institusi   <- profiles.institution
  5. Tanggal     <- timestamp signing, format lokal "DD MMMM YYYY"
  6. Signature ID <- signatures.id
  7. QR-Code     <- dirender pyHanko dari payload FR-07 (lihat pdf/signer.py)

Catatan:
- Bulan memakai daftar Indonesia hardcoded (deterministik, tanpa
  ketergantungan locale OS).
- Field kosong (position/institution boleh NULL) ditampilkan "-" agar
  barisnya tetap ada dan urutan tidak bergeser (fail-closed: tidak ada
  baris yang hilang diam-diam).
"""

from datetime import datetime

BULAN_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

JUDUL = "DITANDATANGANI SECARA DIGITAL"


def format_tanggal_id(dt: datetime) -> str:
    """'DD MMMM YYYY', contoh: 27 September 2026."""
    return f"{dt.day} {BULAN_ID[dt.month - 1]} {dt.year}"


def parse_signed_at(value: str) -> datetime:
    """Parse ISO-8601 dari web. Naif -> anggap UTC. Raise ValueError bila
    tidak bisa di-parse (fail-closed: jangan tebak tanggal)."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt


def build_appearance_text(
    name: str,
    position: str | None,
    institution: str | None,
    signed_at: datetime,
    signature_id: str,
) -> str:
    """Susun teks appearance FR-06 (tanpa QR; QR ditangani QRStampStyle)."""
    if not name or not name.strip():
        raise ValueError("signer_name wajib diisi")
    if not signature_id or not signature_id.strip():
        raise ValueError("signature_id wajib diisi")
    lines = [
        JUDUL,
        f"Nama: {name.strip()}",
        f"Jabatan: {(position or '').strip() or '-'}",
        f"Institusi: {(institution or '').strip() or '-'}",
        f"Tanggal: {format_tanggal_id(signed_at)}",
        f"Signature ID: {signature_id.strip()}",
    ]
    return "\n".join(lines)
