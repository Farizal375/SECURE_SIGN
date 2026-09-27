# Deviations from PRD

## DEV-001: Python Version
- **PRD Requirement**: Python 3.11 or 3.12 (§3)
- **Actual**: Python 3.14.7
- **Reason**: User confirmed to proceed with installed Python 3.14.7
- **Impact**: pyHanko and cryptography libraries function correctly on 3.14. Render deployment may need explicit Python version configuration since Render auto-detects .python-version.
- **Mitigation**: .python-version set to 3.14. Verify Render supports this version before deployment (Phase 15).

## DEV-002: Prisma CLI init
- **PRD Requirement**: Run 
px prisma init --datasource-provider postgresql (§4.2)
- **Actual**: prisma/schema.prisma created manually (identical content to §6)
- **Reason**: Prisma 5.22.0 init command errors on Node.js v24.20.0 ((0 , CSe.isError) is not a function)
- **Impact**: None — the schema file content is identical to what prisma init would generate, plus the full §6 schema.

## DEV-003: Node.js Version
- **PRD Requirement**: Node.js >=20 LTS (§3)
- **Actual**: Node.js v24.20.0
- **Impact**: Minor compatibility issues with Prisma 5 CLI (worked around via DEV-002). Runtime functionality unaffected.

## DEV-004: qrcode version
- **PRD Requirement**: qrcode ^7.x (§3)
- **Actual**: qrcode 8.2 installed (^7.x no longer available, pip resolves to 8.x)
- **Reason**: Fail-closed interpretation — using latest stable is safer than pinning unavailable version.
- **Impact**: API compatible. No breaking changes from 7.x to 8.x for our usage.

## DEV-005: Phase 2 DB setup partially offline
- **PRD Requirement**: `prisma migrate dev` against Supabase (`§14` step 2)
- **Actual**: Initial migration generated offline via `prisma migrate diff --from-empty --to-schema-datamodel prisma/schema.prisma --script`, written to `prisma/migrations/20260927000000_init/migration.sql`; manual partial unique index appended per `§6`. `migration_lock.toml` created manually.
- **Reason**: `.env` was empty (0 bytes); no `DATABASE_URL`/`DIRECT_URL`/`SUPABASE_*` credentials available, so no live DB connection.
- **Impact**: Tables, enums, and RLS policies are authored but not yet applied to Supabase. Once credentials are filled in `.env`, run `prisma migrate deploy` and execute `supabase/policies.sql` separately.
- **Mitigation**: SQL is Prisma-generated (not hand-written table DDL). `prisma validate` passes. Re-run against live DB before continuing to FR-01.

## DEV-006: Removed UTF-8 BOM from schema
- **PRD Requirement**: Valid `prisma/schema.prisma` (`§6`)
- **Actual**: Removed UTF-8 BOM (EF BB BF) from `prisma/schema.prisma`.
- **Reason**: Prisma 5.22.0 validation rejected the file with "This line is invalid" while BOM was present.
- **Impact**: None; schema content unchanged.

## DEV-008: opencv test-only dep + QR render params (backend B4)
- **PRD Requirement**: Test backend pytest (AC-06 QR ter-decode, §13); PRD tidak mengunci decoder QR maupun parameter render QR (box_size/border/error-correction).
- **Actual**: Tambah `opencv-python-headless==4.12.0.88` (pinned) KHUSUS untuk decode QR di test; runtime signer tidak mengimpor cv2. Render QR: `ERROR_CORRECT_M`, `box_size=10`, `border=4` (didokumentasikan di `app/qr/generator.py`).
- **Reason**: AC-06 butuh decode QR nyata; cv2 5.0.0.93 (terbaru) terbukti flaky/tidak stabil me-decode QR kami (hasil non-deterministik antar run), sedangkan 4.12.0 stabil di 3x run.
- **Impact**: Satu dependensi ekstra hanya di venv signer; tidak dipakai kode produksi.

## DEV-007: PRD-UI §11a pending (frontend)
- **PRD Requirement**: Answer all §11a questions before implementing steps 4+ of PRD-UI §16.
- **Actual**: Frontend stopped at PRD-UI §16 step 3 (setup tokens, login, auth callback, AppShell, middleware complete; `tsc --noEmit` and `eslint` pass).
- **Reason**: §11a questions not yet answered by user.
- **Impact**: `documents/new`, `dashboard/`, `documents/`, `documents/[id]`, `sign/[signingRequestId]`, PDF source URL, uploadUrl mechanism, signed-PDF download remain blocked or empty-state until answers are recorded here.

## DEV-009: PSS salt di container CMS + konvensi koordinat + pypdfium2 test (backend B5)
- **PRD Requirement**: Salt PSS 32 byte (§8); koordinat `signature_field` (§10/§11 tidak menyebut origin sumbu-y); test render PDF (AC-05/AC-06).
- **Actual**: (a) Raw PSS tetap salt-32 (B2, teruji). Salt di dalam container CMS/PKCS#7 mengikuti `prefer_pss` pyHanko (optimal) karena API-nya tidak memperbolehkan override — parameter salt tertanam di SignedData sehingga verifikasi tetap self-consistent (B7). (b) `y` diinterpretasi dari ATAS (konvensi PDF.js/react-pdf preview FR-05), dikonversi ke origin kiri-bawah PDF; rotasi halaman diabaikan (MVP). (c) Tambah `pypdfium2==5.13.0` (pinned) KHUSUS test render/parse PDF; runtime tidak memakainya.
- **Reason**: Fail-closed + satu-satunya interpretasi yang konsisten dengan preview frontend; rotasi di luar cakupan MVP.
- **Impact**: Frontend WAJIB kirim `y` dari atas; bila backend/frontend beda interpretasi, posisi signature cermin vertikal (mudah dideteksi visual, 3 baris untuk mengubah).

## DEV-010: Perluasan skema /sign + perilaku /verify (backend B6)
- **PRD Requirement**: Skema request/response §11; error codes signer tidak dirinci PRD.
- **Actual**: (a) `POST /sign` = skema §11 + 7 field terkunci (`encrypted_private_key_base64`, `signer_name`, `signer_position`, `signer_institution`, `signed_at`, `verification_url`, `signature_id`) sesuai keputusan user; `key_id` hanya echo/korelasi (signer stateless, tanpa DB). (b) Extra field di root request DITOLAK (`extra=forbid`, 422) agar drift kontrak ketahuan. (c) Input invalid -> `422 INVALID_REQUEST`; `public_key_fingerprint` = null bila tanpa signature field. (d) Kerja CPU (sign/verify) via `anyio.to_thread` karena `PdfSigner.sign_pdf` sync memanggil `asyncio.run()` di dalamnya (nested-loop error bila di event loop) sekaligus agar tak block loop uvicorn.
- **Reason**: Fail-closed; satu-satunya cara memenuhi FR-02/FR-03 + FR-06/FR-07 tanpa akses DB di signer.
- **Impact**: Kontrak beku untuk frontend (lihat handoff B6); penambahan field butuh persetujuan user.

## DEV-011: Semantik signature_valid + HTTP tamper (backend B7)
- **PRD Requirement**: FR-09 boolean independen; FR-10 tamper -> documentIntegrity:false + signatureValid:false.
- **Actual**: `signature_valid = pyHanko.valid AND pyHanko.intact` (pyHanko memisahkan keaslian CMS dari digest ByteRange; signature atas konten ter-tamper wajib false). Tamper di luar maupun di dalam /Contents -> HTTP tetap 200 + semua false (bukan 4xx); hanya non-PDF (magic bytes) -> 422.
- **Reason**: Satu-satunya pemetaan yang memenuhi FR-10 tanpa melanggar independensi boolean FR-09 (qrValid/publicKeyMatch tetap wewenang web).
- **Impact**: Frontend boleh mengandalkan HTTP 200 + boolean untuk semua kasus dokumen ter-parse.
