# PRD-AGENT — SecureSign
## Spesifikasi Teknis Eksekutabel 

Dokumen ini adalah satu-satunya sumber kebenaran untuk implementasi. Tidak ada bagian naratif, tidak ada justifikasi desain, tidak ada materi untuk pembaca manusia. Setiap baris adalah instruksi yang harus dieksekusi persis seperti tertulis.

---

## 1. Tujuan Sistem 

Bangun aplikasi web dua-layanan bernama **SecureSign** yang:

1. Menerima upload PDF.
2. Menghasilkan pasangan kunci RSA-2048 per akun Signer.
3. Menandatangani PDF secara kriptografis menggunakan RSA-PSS + SHA-256, dengan signature tertanam di struktur PDF (bukan file `.sig` terpisah).
4. Menempelkan QR-Code pada PDF yang hanya berisi URL verifikasi.
5. Memverifikasi PDF: valid bila signature, integritas ByteRange, dan public key cocok; invalid bila salah satu gagal.
6. Menyediakan benchmark waktu signing dan verifikasi (≥30 percobaan).

Referensi RFC 2119: **WAJIB** = harus diimplementasikan persis; **DILARANG** = tidak boleh diimplementasikan sama sekali; **BOLEH** = opsional, boleh diabaikan tanpa mengurangi Definition of Done.

---

## 2. Aturan Kerja Agent (WAJIB dipatuhi sepanjang implementasi)

1. **DILARANG** menebak parameter yang tidak ada di dokumen ini (versi library, nama field, default kriptografi, format response). Jika dibutuhkan dan tidak tercantum → berhenti, ajukan pertanyaan ke pengguna sebelum menulis kode.
2. **DILARANG** menulis implementasi kriptografi sendiri (RSA, PSS, SHA-256 custom). WAJIB pakai library yang dikunci di §3.
3. Saat ada dua interpretasi valid atas suatu requirement, pilih interpretasi yang **fail-closed** (lebih ketat/lebih aman), lalu catat asumsi tersebut sebagai komentar kode + entri di `docs/deviations.md`.
4. Setiap requirement fungsional (§7) WAJIB memiliki test otomatis yang membuktikan kriteria di §13 sebelum ditandai selesai. Tidak ada requirement yang "selesai" hanya berdasarkan review visual.
5. Ikuti urutan implementasi di §14 secara berurutan. Jangan mengerjakan tahap N+1 sebelum tahap N lulus test.
6. Semua nilai numerik, nama field, dan nama endpoint di dokumen ini bersifat final dan mengikat. Tidak boleh diubah tanpa instruksi eksplisit dari pengguna.

---

## 3. Tech Stack (Terkunci)

| Layer | Teknologi | Versi |
|---|---|---|
| Web framework | Next.js, App Router | `^15.x` |
| Runtime web | Node.js | `>=20 LTS` |
| Bahasa web | TypeScript, `strict: true` | `^5.x` |
| Styling | Tailwind CSS | `^3.x` |
| Komponen UI | shadcn/ui | terbaru saat setup |
| Auth | Supabase Auth, **OAuth only** (provider WAJIB: Google) | Supabase JS client `^2.x` |
| ORM / DB access | **Prisma ORM** (`prisma`, `@prisma/client`) | `^5.x` |
| Database | Supabase PostgreSQL, diakses lewat Prisma via connection pooling (bukan Supabase query builder) | Postgres `15.x` |
| Object storage | Cloudflare R2 (S3-compatible) | `@aws-sdk/client-s3` `^3.x` |
| Signing service | FastAPI | `^0.115.x` |
| Runtime signing service | Python | `3.11` atau `3.12` (WAJIB sama di semua environment) |
| Kriptografi | `cryptography` (Python) | `>=42,<44` |
| PDF signing/verify | `pyHanko` | `>=0.25,<0.30` |
| QR generation | `qrcode` (Python) | `^7.x` |
| PDF preview frontend | `react-pdf` | `^9.x` |
| Test backend | `pytest` | `^8.x` |
| Test frontend | Vitest + Playwright | terbaru saat setup |
| Hosting web | Vercel Hobby | — |
| Hosting signing service | Render Free, **native Python runtime** (build command `pip install -r requirements.txt`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`) | — |
| Repo | 1 GitHub monorepo | — |

Setelah instalasi pertama, WAJIB kunci versi persis di `package-lock.json` dan `requirements.txt` (pinned, tanpa `>=`/`^` longgar).

Karena tidak memakai Docker, versi Python untuk `services/signer` WAJIB dikunci lewat file `services/signer/.python-version` (isi: `3.11` atau `3.12`, harus identik dengan yang dipilih di §3) dan dikonfirmasi sama persis di pengaturan environment Render (Render mendeteksi `.python-version` secara otomatis untuk native Python runtime). DILARANG ada perbedaan versi Python antara lokal dan Render.

**Pembagian tanggung jawab (WAJIB dipahami agar tidak tertukar):**
- **Supabase** menyediakan: (a) Postgres sebagai database fisik, (b) Supabase Auth khusus untuk OAuth login (Google) dan pengelolaan session/JWT. Supabase TIDAK dipakai sebagai query builder data aplikasi.
- **Prisma** adalah satu-satunya cara aplikasi Next.js (server-side) membaca/menulis tabel `profiles`, `documents`, `signing_keys`, dll. DILARANG memakai `supabase-js` `.from(...)` untuk query tabel aplikasi — `supabase-js` HANYA dipakai untuk `supabase.auth.*` (OAuth flow, ambil session).
- Prisma DILARANG dipanggil dari browser/client component. Semua akses Prisma WAJIB lewat Server Component, Route Handler, atau Server Action di Next.js.

---

## 4. Struktur Direktori & Setup Proyek (WAJIB)

Bagian ini adalah **Tahap 0**: agent WAJIB mengeksekusi §4.2 secara langsung (menjalankan perintah, bukan hanya mendeskripsikan) sebagai tindakan pertama sebelum menyentuh §14 langkah 1. Hasil akhirnya WAJIB persis strukturnya seperti §4.1.

### 4.1 Struktur Direktori Final (Target)

```text
securesign/
├── apps/web/
│   ├── app/
│   │   ├── auth/callback/        # OAuth callback route handler
│   │   ├── (auth)/               # halaman login ("Masuk dengan Google")
│   │   ├── dashboard/
│   │   ├── documents/
│   │   ├── sign/
│   │   ├── verify/
│   │   └── api/v1/
│   ├── components/
│   ├── lib/{prisma,supabase-auth,r2,validation}/
│   └── tests/
├── prisma/
│   ├── schema.prisma              # sumber kebenaran skema DB (§6)
│   └── migrations/                # dihasilkan `prisma migrate dev/deploy`
├── services/signer/
│   ├── app/{main.py,api/,crypto/,pdf/,qr/,verification/,security/}
│   ├── tests/
│   ├── requirements.txt
│   └── .python-version
├── supabase/{policies.sql}          # RLS policies saja — migration tabel via Prisma, BUKAN di sini
├── scripts/{benchmark.py,generate-demo-key.py}
├── .env.example
└── README.md
```

`apps/web` dan `services/signer` WAJIB punya dependency, runtime, dan deployment terpisah meski satu repo.

### 4.2 Perintah Setup Awal (Tahap 0 — WAJIB dieksekusi agent secara langsung, berurutan, di terminal proyek)

Agent WAJIB menjalankan blok perintah berikut apa adanya (menyesuaikan hanya jika versi tool terbaru menolak sebuah flag), bukan menebak struktur sendiri. Jika salah satu perintah gagal karena versi CLI berbeda dari yang tertulis di §3, agent WAJIB berhenti dan bertanya ke pengguna sebelum melanjutkan (§2 aturan 1) — DILARANG melompati langkah yang gagal.

```bash
# --- 0. Inisialisasi repo ---
mkdir -p securesign && cd securesign
git init

cat > .gitignore << 'EOF'
node_modules/
.next/
.env
.env.local
*.pem
*.key
*.p12
*.enc
services/signer/.venv/
services/signer/**/__pycache__/
EOF

# --- 1. Rangka folder dasar (isi lengkap menyusul di tahap FR masing-masing) ---
mkdir -p prisma supabase scripts
mkdir -p services/signer/app/{api,crypto,pdf,qr,verification,security}
mkdir -p services/signer/tests

# --- 2. apps/web: Next.js 15, App Router, TS strict, Tailwind ---
npx create-next-app@15 apps/web \
  --typescript --tailwind --eslint --app \
  --no-src-dir --import-alias "@/*" --use-npm

cd apps/web
npx shadcn@latest init   # terima default kecuali pengguna menentukan lain
mkdir -p components lib/prisma lib/supabase-auth lib/r2 lib/validation tests
npm install @supabase/supabase-js @aws-sdk/client-s3 react-pdf
npm install --save-dev vitest @playwright/test
cd ..

# --- 3. Prisma (root repo, BUKAN di dalam apps/web — lihat §4.1) ---
npm init -y
npm install --save-dev prisma
npm install @prisma/client
npx prisma init --datasource-provider postgresql
# lanjutkan isi prisma/schema.prisma persis sesuai §6 — DILARANG menambah field di luar §6

# --- 4. services/signer: FastAPI + Python ---
cd services/signer
# WAJIB konfirmasi ke pengguna versi patch Python persis (mis. 3.11.9 atau 3.12.x)
# sebelum menuliskannya ke .python-version — DILARANG menebak (§2 aturan 1)
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install "fastapi>=0.115,<0.116" "uvicorn[standard]" \
  "cryptography>=42,<44" "pyHanko>=0.25,<0.30" "qrcode[pil]" \
  pytest httpx
pip freeze > requirements.txt
touch app/__init__.py app/main.py
deactivate
cd ../..

# --- 5. File konfigurasi & dokumentasi root ---
touch .env.example README.md
touch supabase/policies.sql
touch scripts/benchmark.py scripts/generate-demo-key.py
```

Setelah blok di atas selesai:
1. Isi `.env.example` dengan seluruh variabel di §5 (nama saja, tanpa nilai).
2. Jalankan ulang `git add -A && git status` untuk memastikan tidak ada `.env`, `*.pem`, `*.key`, `*.p12`, `*.enc` yang ikut ter-stage (cross-check AC-04).
3. Lanjutkan ke §14 langkah 2 (setup Supabase + Prisma schema).

### 4.3 Menjalankan Lokal (tanpa Docker)

- `services/signer`: aktifkan `.venv`, `pip install -r requirements.txt` (bila clone baru), jalankan `uvicorn app.main:app --reload --port 8000`.
- `apps/web`: `npm install`, lalu `npm run dev` (Next.js dev server, default port `3000`).
- Kedua proses dijalankan langsung di OS/terminal pengembang (bukan container), terhubung ke instance Supabase Postgres (cloud, bukan lokal) lewat `DATABASE_URL`/`DIRECT_URL` di `.env`. `SIGNER_SERVICE_URL` di `apps/web/.env` diarahkan ke `http://localhost:8000`.

---

## 5. Environment Variables (WAJIB, semua harus ada di `.env.example` tanpa nilai)

| Variable | Wajib di | Format | Keterangan |
|---|---|---|---|
| `DATABASE_URL` | web | postgresql URL, port `6543`, `?pgbouncer=true` | dipakai Prisma Client runtime (pooled connection ke Supabase Postgres) |
| `DIRECT_URL` | web | postgresql URL, port `5432` | dipakai HANYA oleh `prisma migrate` (koneksi langsung, bukan pooled) |
| `SUPABASE_URL` | web | URL | dipakai HANYA untuk `supabase.auth.*` (OAuth), bukan query data |
| `SUPABASE_ANON_KEY` | web (client) | string | dipakai HANYA untuk `supabase.auth.*` di client component |
| `SUPABASE_SERVICE_ROLE_KEY` | web (server-only) | string | BOLEH, hanya untuk operasi admin Supabase Auth API (mis. hapus user); DILARANG dikirim ke browser; DILARANG dipakai untuk query tabel data (itu tugas Prisma) |
| `NEXT_PUBLIC_SITE_URL` | web | URL | base URL untuk redirect OAuth callback, mis. `https://securesign.vercel.app` |
| `R2_ACCOUNT_ID` | web | string | — |
| `R2_ACCESS_KEY_ID` | web | string | — |
| `R2_SECRET_ACCESS_KEY` | web | string | — |
| `R2_BUCKET` | web | string | — |
| `SIGNER_SERVICE_URL` | web | URL | base URL FastAPI |
| `SIGNER_SERVICE_SECRET` | web + signer | string acak ≥32 byte | shared secret, lihat §9 |
| `PRIVATE_KEY_ENCRYPTION_KEY` | signer | 32 byte, base64 | key AES-256-GCM |
| `MAX_UPLOAD_SIZE_MB` | web | integer | default `10` |
| `MAX_PDF_PAGES` | web | integer | default `20` |

Konfigurasi Google OAuth (Client ID/Secret) diatur di Supabase Dashboard → Authentication → Providers, **bukan** sebagai environment variable aplikasi.

File yang DILARANG masuk Git: `.env`, `.env.local`, `*.pem`, `*.key`, `*.p12`, `*.enc`.

---

## 6. Skema Database (Prisma Schema — SUMBER TUNGGAL)

`prisma/schema.prisma` adalah satu-satunya sumber kebenaran struktur data. DILARANG menulis migration SQL manual untuk tabel aplikasi — WAJIB dihasilkan dari file ini via `prisma migrate dev` (lokal) / `prisma migrate deploy` (production, dijalankan di build step Vercel).

```prisma
datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_URL")
}

generator client {
  provider = "prisma-client-js"
}

enum UserRole {
  admin_secretary
  signer
  public_verifier

  @@map("user_role")
}

enum DocumentStatus {
  DRAFT
  UPLOADED
  READY
  SIGNING
  SIGNED
  INVALID
  REVOKED

  @@map("document_status")
}

enum SigningRequestStatus {
  PENDING
  SIGNED
  EXPIRED
  CANCELLED

  @@map("signing_request_status")
}

// id WAJIB sama persis dengan auth.users.id milik Supabase Auth.
// TIDAK ada @default(uuid()) di sini — nilai id diisi manual dari session OAuth saat upsert pertama kali (lihat FR-01).
model Profile {
  id          String   @id @db.Uuid
  fullName    String   @map("full_name")
  email       String   @unique
  role        UserRole @default(signer)
  position    String?
  institution String?
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt @map("updated_at")

  documents        Document[]
  signingKeys      SigningKey[]
  signingRequests  SigningRequest[]
  signatures       Signature[]
  auditLogs        AuditLog[]

  @@map("profiles")
}

model Document {
  id                  String         @id @default(uuid()) @db.Uuid
  ownerId             String         @map("owner_id") @db.Uuid
  owner               Profile        @relation(fields: [ownerId], references: [id])
  originalFilename    String         @map("original_filename")
  mimeType            String         @map("mime_type")
  fileSize            BigInt         @map("file_size")
  sourceSha256        String         @map("source_sha256") @db.Char(64)
  storageOriginalPath String         @map("storage_original_path")
  storageSignedPath   String?        @map("storage_signed_path")
  status              DocumentStatus @default(DRAFT)
  createdAt           DateTime       @default(now()) @map("created_at")
  updatedAt           DateTime       @updatedAt @map("updated_at")

  signingRequests     SigningRequest[]
  signatures          Signature[]
  verificationRecords VerificationRecord[]
  auditLogs           AuditLog[]

  @@index([ownerId])
  @@map("documents")
}

model SigningKey {
  id                   String    @id @default(uuid()) @db.Uuid
  ownerId              String    @map("owner_id") @db.Uuid
  owner                Profile   @relation(fields: [ownerId], references: [id])
  algorithm            String    @default("RSA")
  keySize              Int       @default(2048) @map("key_size")
  publicKeyPem         String    @map("public_key_pem")
  publicKeyFingerprint String    @map("public_key_fingerprint") @db.Char(64)
  encryptedPrivateKey  Bytes     @map("encrypted_private_key")
  encryptionAlgorithm  String    @default("AES-256-GCM") @map("encryption_algorithm")
  createdAt            DateTime  @default(now()) @map("created_at")
  rotatedAt            DateTime? @map("rotated_at")

  signatures Signature[]

  @@map("signing_keys")
}

model SigningRequest {
  id         String               @id @default(uuid()) @db.Uuid
  documentId String               @map("document_id") @db.Uuid
  document   Document             @relation(fields: [documentId], references: [id])
  signerId   String               @map("signer_id") @db.Uuid
  signer     Profile              @relation(fields: [signerId], references: [id])
  status     SigningRequestStatus @default(PENDING)
  requestedAt DateTime            @default(now()) @map("requested_at")
  signedAt   DateTime?            @map("signed_at")
  expiresAt  DateTime             @map("expires_at")

  signaturePositions SignaturePosition[]

  @@index([documentId])
  @@map("signing_requests")
}

model SignaturePosition {
  id               String         @id @default(uuid()) @db.Uuid
  signingRequestId String         @map("signing_request_id") @db.Uuid
  signingRequest   SigningRequest @relation(fields: [signingRequestId], references: [id])
  pageNumber       Int            @map("page_number")
  x                Decimal
  y                Decimal
  width            Decimal
  height           Decimal

  @@map("signature_positions")
}

model Signature {
  id                     String     @id @default(uuid()) @db.Uuid
  documentId             String     @map("document_id") @db.Uuid
  document               Document   @relation(fields: [documentId], references: [id])
  signerId               String     @map("signer_id") @db.Uuid
  signer                 Profile    @relation(fields: [signerId], references: [id])
  signingKeyId           String     @map("signing_key_id") @db.Uuid
  signingKey             SigningKey @relation(fields: [signingKeyId], references: [id])
  algorithm              String     @default("RSA-PSS")
  hashAlgorithm          String     @default("SHA-256") @map("hash_algorithm")
  keyAlgorithm           String     @default("RSA-2048") @map("key_algorithm")
  publicKeyFingerprint   String     @map("public_key_fingerprint") @db.Char(64)
  signatureFingerprint   String     @map("signature_fingerprint") @db.Char(64)
  signedPdfSha256        String     @map("signed_pdf_sha256") @db.Char(64)
  signedAt               DateTime   @default(now()) @map("signed_at")
  verificationTokenHash  String     @unique @map("verification_token_hash") @db.Char(64)
  createdAt              DateTime   @default(now()) @map("created_at")

  verificationRecords VerificationRecord[]

  @@index([documentId])
  @@map("signatures")
}

model VerificationRecord {
  id           String    @id @default(uuid()) @db.Uuid
  documentId   String    @map("document_id") @db.Uuid
  document     Document  @relation(fields: [documentId], references: [id])
  signatureId  String    @map("signature_id") @db.Uuid
  signature    Signature @relation(fields: [signatureId], references: [id])
  tokenHash    String    @unique @map("token_hash") @db.Char(64)
  publicStatus Boolean   @default(true) @map("public_status")
  createdAt    DateTime  @default(now()) @map("created_at")

  @@map("verification_records")
}

model AuditLog {
  id                 BigInt   @id @default(autoincrement())
  actorId            String?  @map("actor_id") @db.Uuid
  actor              Profile? @relation(fields: [actorId], references: [id])
  eventType          String   @map("event_type")
  documentId         String?  @map("document_id") @db.Uuid
  document           Document? @relation(fields: [documentId], references: [id])
  signatureId        String?  @map("signature_id") @db.Uuid
  ipHash             String?  @map("ip_hash") @db.Char(64)
  userAgent          String?  @map("user_agent")
  metadata           Json     @default("{}")
  previousEventHash  String?  @map("previous_event_hash") @db.Char(64)
  eventHash          String   @map("event_hash") @db.Char(64)
  createdAt          DateTime @default(now()) @map("created_at")

  @@index([documentId])
  @@map("audit_logs")
}
```

**Keterbatasan Prisma yang WAJIB ditangani manual:** Prisma schema di atas TIDAK bisa menyatakan partial unique index (`WHERE rotated_at IS NULL`) untuk memastikan satu `owner_id` hanya punya satu `signing_keys` aktif. Setelah `prisma migrate dev` membuat migration awal, agent WAJIB menambah baris berikut ke file migration `.sql` yang dihasilkan (edit manual, migration tetap tervalidasi Prisma):
```sql
create unique index idx_signing_keys_owner_active on signing_keys(owner_id) where rotated_at is null;
```

**Perubahan model otorisasi (WAJIB dipahami — ini mengoreksi asumsi "RLS = lapisan otorisasi utama"):**
- Karena Prisma terhubung ke Postgres lewat connection pooling langsung (bukan lewat Supabase PostgREST), **RLS TIDAK otomatis berlaku untuk query Prisma**. Prisma berjalan dengan role database yang bisa membaca semua baris.
- **Otorisasi utama WAJIB dilakukan di application layer**: setiap query Prisma yang mengambil/mengubah data milik user WAJIB menyertakan filter eksplisit, contoh: `prisma.document.findMany({ where: { ownerId: session.user.id } })`. DILARANG melakukan query tanpa filter kepemilikan lalu menyaring hasilnya di kode — filter WAJIB ada di level query.
- RLS (`alter table ... enable row level security`) tetap WAJIB diaktifkan di Supabase sebagai defense-in-depth, dengan policy yang sama seperti sebelumnya (`owner_id = auth.uid()` dsb.), untuk berjaga-jaga bila suatu saat ada akses langsung dari Supabase client. Policy ini ditulis di `supabase/policies.sql` dan dijalankan terpisah dari migration Prisma.
- `event_hash = SHA256(event_data_json + previous_event_hash)`. Event pertama: `previous_event_hash = ''`.
- Event type yang WAJIB dicatat: `USER_LOGIN`, `DOCUMENT_CREATED`, `DOCUMENT_UPLOADED`, `SIGNING_REQUEST_CREATED`, `QR_CREATED`, `SIGNING_STARTED`, `SIGNING_SUCCESS`, `SIGNING_FAILED`, `DOCUMENT_VERIFIED`, `DOCUMENT_TAMPER_DETECTED`, `WRONG_KEY_DETECTED`, `QR_FORGERY_DETECTED`, `DOCUMENT_DOWNLOADED`.

---

## 7. Functional Requirements (Direktif)

**FR-01 Authentication (OAuth only)** — Login WAJIB hanya lewat OAuth, provider WAJIB: **Google**. DILARANG mengimplementasikan form email/password.

Alur wajib:
1. Tombol "Masuk dengan Google" di halaman `(auth)` memanggil `supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: \`${NEXT_PUBLIC_SITE_URL}/auth/callback\` } })` di client component.
2. Redirect Google consent screen → kembali ke `GET /auth/callback?code=...`.
3. Route handler `/auth/callback` (server) memanggil `supabase.auth.exchangeCodeForSession(code)`, menyimpan session ke cookie.
4. Server WAJIB cek via Prisma: `prisma.profile.findUnique({ where: { id: user.id } })`. Jika `null` → buat baru: `prisma.profile.create({ data: { id: user.id, email: user.email, fullName: user.user_metadata.full_name ?? user.email, role: 'signer' } })`. Role selain `signer` (yaitu `admin_secretary`) DILARANG di-assign otomatis — hanya diubah manual di database oleh operator.
5. Redirect ke `/dashboard`.
6. Insert `audit_logs` event `USER_LOGIN`.

Session: dikelola oleh cookie Supabase Auth (access + refresh token JWT). Middleware Next.js WAJIB memvalidasi session pada semua route privat; tanpa session valid → redirect ke halaman login (untuk halaman) atau `401 UNAUTHENTICATED` (untuk API route). Role `public_verifier` (pengguna publik yang hanya scan QR/upload PDF untuk verifikasi) tidak butuh login sama sekali — endpoint verifikasi publik (`/api/v1/verify`, `/api/v1/verify/{token}`, `GET /verify/{token}`) tetap tanpa auth.

Provider OAuth lain (GitHub, Microsoft) BOLEH ditambahkan sebagai enhancement, tidak wajib MVP.

**FR-02 Key Generation** — Saat akun dengan role `signer` pertama kali dibuat DAN belum punya baris di `signing_keys` dengan `rotated_at is null`: generate RSA-2048 key pair, enkripsi private key (lihat FR-03), simpan. Public key boleh dibaca bebas oleh pemiliknya. Private key DILARANG: ada di source code, dikirim ke browser, disimpan plaintext.

**FR-03 Private Key Encryption** — Alur wajib: `RSA private key (DER)` → `AES-256-GCM` dengan key dari `PRIVATE_KEY_ENCRYPTION_KEY` → simpan sebagai `bytea` di `signing_keys.encrypted_private_key`. Nonce/IV unik per enkripsi, disimpan bersama ciphertext (prefix 12 byte). Dekripsi HANYA boleh terjadi di proses `services/signer`, tidak pernah di `apps/web`.

**FR-04 PDF Upload** — Validasi berurutan, tolak pada kegagalan pertama:
1. Ekstensi `.pdf` (case-insensitive) → gagal: `400 VALIDATION_ERROR`.
2. Ukuran ≤ `MAX_UPLOAD_SIZE_MB` (default 10 MB) → gagal: `413 FILE_TOO_LARGE`.
3. Magic bytes file diawali `%PDF-` → gagal: `422 PDF_UNREADABLE`.
4. Berhasil di-parse library PDF, tidak berpassword/terenkripsi → gagal: `422 PDF_UNREADABLE`.
5. Jumlah halaman ≤ `MAX_PDF_PAGES` (default 20) → gagal: `422 PDF_TOO_MANY_PAGES`.
Setelah lolos: hitung `source_sha256 = SHA256(file_bytes)` (hex, 64 char), simpan ke R2 `original/{document_id}.pdf`.

**FR-05 Document Preview & Signature Position** — Endpoint mengembalikan jumlah halaman + render URL per halaman (via `react-pdf`). User memilih `page`, `x`, `y`, `width>0`, `height>0` dalam satuan point PDF. Nilai disimpan ke `signature_positions`.

**FR-06 Signature Appearance** — Visual signature yang di-render ke PDF WAJIB memuat field berikut, dalam urutan ini: judul "DITANDATANGANI SECARA DIGITAL", `Nama` (dari `profiles.full_name`), `Jabatan` (dari `profiles.position`), `Institusi` (dari `profiles.institution`), `Tanggal` (timestamp signing, format lokal `DD MMMM YYYY`), `Signature ID` (= `signatures.id`), dan gambar QR-Code (§8).

**FR-07 QR-Code** — Payload QR HANYA:
```json
{ "verificationUrl": "https://<domain>/verify/<verification-token>" }
```
DILARANG memasukkan field lain (nama, jabatan, institusi, documentId, signatureId) ke dalam QR. `verification-token` = 32 byte random URL-safe base64, disimpan sebagai `SHA256(token)` hex di `signatures.verification_token_hash` dan `verification_records.token_hash`. Token plaintext HANYA ada di URL QR, tidak pernah disimpan.

**FR-08 Embedded PDF Signature** — Signature WAJIB tertanam di struktur PDF (`/AcroForm`, `/Sig`, `/ByteRange`, `/Contents`) menggunakan `pyHanko`. DILARANG membuat struktur signature PDF manual/dari nol. Output akhir: satu file `signed.pdf`, bukan `document.pdf` + `signature.sig` terpisah.

**FR-09 Verification** — Urutan pengecekan WAJIB, berhenti di kegagalan pertama dan set field terkait `false`:
1. PDF dapat diparse.
2. Signature field ditemukan di PDF.
3. `/ByteRange` valid dan mencakup seluruh isi PDF kecuali area `/Contents`.
4. Digest byte dalam ByteRange dihitung ulang dan dibandingkan.
5. RSA-PSS signature diverifikasi memakai public key yang tersimpan.
6. `signatures.public_key_fingerprint` cocok dengan fingerprint public key yang dipakai verifikasi.
Response WAJIB persis field ini:
```json
{
  "valid": true,
  "documentIntegrity": true,
  "signatureValid": true,
  "publicKeyMatch": true,
  "qrValid": true,
  "signer": { "name": "...", "position": "...", "institution": "..." },
  "signedAt": "2026-09-26T10:00:00Z"
}
```
Semua field boolean bernilai independen — jangan short-circuit ke `false` semua bila satu gagal; laporkan yang mana yang gagal.

**FR-10 Tamper Detection** — Mengubah 1 byte konten PDF di luar `/Contents` WAJIB menghasilkan `documentIntegrity: false` dan `signatureValid: false` pada FR-09.

**FR-11 Wrong Public Key** — Verifikasi dengan public key selain yang dipakai signing WAJIB menghasilkan `signatureValid: false`, `publicKeyMatch: false`.

**FR-12 Token/QR Tidak Valid** — Token yang tidak ada di `verification_records` WAJIB menghasilkan `qrValid: false` / `tokenValid: false`, TANPA membocorkan apakah token "salah format" vs "tidak terdaftar" (respons sama untuk kedua kasus, status HTTP `200`).

---

## 8. Parameter Kriptografi (Terkunci)

| Parameter | Nilai |
|---|---|
| Algoritma kunci | RSA, modulus 2048 bit |
| Public exponent | 65537 |
| Algoritma signature | RSA-PSS |
| Hash | SHA-256 |
| MGF | MGF1 dengan SHA-256 |
| Salt length | 32 byte (= digest size SHA-256). DILARANG pakai `PSS.MAX_LENGTH`. |
| Enkripsi private key | AES-256-GCM, nonce 12 byte unik per operasi |
| Public key fingerprint | `SHA256(SPKI DER)`, hex lowercase, 64 karakter |
| PDF signature container | CMS/PKCS#7 detached, dibuat oleh `pyHanko` |

---

## 9. Autentikasi Antar-Layanan

Header wajib pada setiap request `apps/web` (server-side) → `services/signer`:
```
X-Signer-Service-Secret: <SIGNER_SERVICE_SECRET>
```
`services/signer` WAJIB membandingkan dengan `hmac.compare_digest`, bukan `==`. Tanpa header valid → `401`. Endpoint signing service DILARANG diekspos langsung ke browser/publik (hanya dipanggil dari server Next.js).

---

## 10. API Contract — Next.js (`/api/v1/...`)

Format error seragam untuk semua endpoint:
```json
{ "error": { "code": "FILE_TOO_LARGE", "message": "...", "details": {} } }
```

| Method & Path | Auth | Request | Response 200/201 | Error Codes |
|---|---|---|---|---|
| `POST /api/v1/documents` | session | `{ "filename": "surat.pdf" }` | `{ "documentId": "uuid", "uploadUrl": "..." }` | 400, 401 |
| `POST /api/v1/documents/{id}/upload-complete` | session | `{}` | `{ "documentId": "uuid", "sourceSha256": "hex64", "pageCount": 12, "status": "READY" }` | 401, 403, 404, 413, 422 |
| `POST /api/v1/signing-requests` | session | `{ "documentId":"uuid","signerId":"uuid","page":1,"x":350,"y":100,"width":180,"height":80 }` | `{ "signingRequestId": "uuid", "expiresAt": "ISO-8601" }` | 400, 401, 403, 404 |
| `POST /api/v1/signatures` | session | `{ "signingRequestId": "uuid" }` | `{ "signatureId": "uuid", "documentId": "uuid", "status": "SIGNED" }` | 401, 403, 404, 409 (`SIGNING_REQUEST_EXPIRED`), 502 (`SIGNING_SERVICE_UNAVAILABLE`) |
| `POST /api/v1/verify` | publik | multipart `file=<pdf>` | schema FR-09 | 400, 422 |
| `GET /verify/{token}` | publik | — | halaman HTML (bukan JSON), memanggil endpoint di bawah | — |
| `POST /api/v1/verify/{token}` | publik | multipart `file=<pdf>` | schema FR-09 + `"tokenValid": true` | 400 (respons `200` dengan `tokenValid:false` bila token tak ditemukan, BUKAN 404) |

Rate limit: endpoint publik verifikasi = 10 req/menit/IP. Endpoint signing = 20 req/menit/user. Lewat limit → `429 RATE_LIMITED`.

---

## 11. API Contract — Internal Signing Service (FastAPI)

**`POST /sign`**
Request:
```json
{
  "document_base64": "...",
  "key_id": "uuid",
  "signature_field": { "page": 0, "x": 100, "y": 100, "width": 180, "height": 80 }
}
```
Response `200`:
```json
{
  "signed_document_base64": "...",
  "signature_algorithm": "RSA-PSS",
  "hash_algorithm": "SHA-256",
  "public_key_fingerprint": "hex64"
}
```

**`POST /verify`**
Request: `{ "document_base64": "..." }`
Response `200`: `{ "valid": true, "integrity": true, "signature_valid": true, "public_key_fingerprint": "hex64" }`

Kedua endpoint WAJIB memvalidasi header `X-Signer-Service-Secret` (§9) sebelum memproses body.

---

## 12. Alur Wajib (Ordered, implementasikan persis urutan ini)

**Signing:**
```
1. Middleware cek session Supabase Auth (FR-01, OAuth) → ambil `session.user.id` → pastikan baris `profiles` ada (dibuat saat callback OAuth, lihat FR-01 langkah 4)
2. Jika signer belum punya signing_keys aktif (query Prisma: `signingKeys.findFirst({ where: { ownerId, rotatedAt: null } })`) → jalankan FR-02 (generate + encrypt key)
3. Upload PDF → validasi FR-04 → hitung source_sha256 → simpan R2 original/{id}.pdf → insert documents (Prisma `prisma.document.create`)
4. Insert signing_requests (status PENDING, expires_at = now()+24h)
5. Insert signature_positions
6. Generate verification token (32 byte) → insert signatures.verification_token_hash + verification_records.token_hash (hash saja)
7. Generate QR dari verificationUrl (FR-07)
8. Susun visible signature appearance (FR-06) + QR ke PDF
9. Panggil POST /sign ke signing service (§9, §11)
10. Signing service: hitung digest ByteRange → SHA-256 → RSA-PSS sign → embed /Contents (FR-08)
11. Next.js terima signed_document_base64 → jalankan self-verification: panggil POST /verify internal
12. Jika self-verify gagal → status SIGNING_FAILED, JANGAN simpan PDF, JANGAN set status SIGNED
13. Jika self-verify berhasil → simpan signed.pdf ke R2 signed/{id}.pdf → hitung signed_pdf_sha256 → update documents.status = SIGNED, signing_requests.status = SIGNED
14. Insert audit_logs (event SIGNING_SUCCESS atau SIGNING_FAILED)
```

**Verifikasi via QR:**
```
1. GET /verify/{token} → render halaman upload
2. User upload PDF
3. POST /api/v1/verify/{token} → lookup token_hash di verification_records
   - tidak ada → return tokenValid:false, valid:false (HTTP 200)
   - ada → lanjut ke FR-09 penuh, ambil metadata signer dari verification_records/signatures (BUKAN dari QR)
4. Insert audit_logs (DOCUMENT_VERIFIED / DOCUMENT_TAMPER_DETECTED / WRONG_KEY_DETECTED sesuai hasil)
```

**Verifikasi via Direct Upload:** sama seperti di atas mulai langkah 3, memakai `POST /api/v1/verify` (tanpa token).

---

## 13. Test Wajib & Acceptance Criteria (Executable — WAJIB diimplementasikan sebagai test otomatis)

| ID | Test | Assertion Konkret |
|---|---|---|
| AC-01 | Upload PDF valid ≤10MB | `POST /api/v1/documents` + upload-complete → `200`, `documentId` UUID v4 valid |
| AC-02 | Key generation | private/public key pair RSA modulus tepat 2048 bit, `n.bit_length() == 2048` |
| AC-03 | Private key terenkripsi | `signing_keys.encrypted_private_key` bukan valid PEM/DER RSA key mentah (gagal diparse langsung sebagai private key) |
| AC-04 | Tidak ada private key plaintext di Git | `git grep -i "BEGIN RSA PRIVATE KEY"` di seluruh riwayat commit = 0 hasil |
| AC-05 | Signature appearance | field FR-06 semua muncul di rendered PDF page |
| AC-06 | QR tertanam | QR ter-decode dari halaman PDF menghasilkan persis `verificationUrl` sesuai FR-07 |
| AC-07 | Digital signature tertanam | PDF hasil punya `/ByteRange` dan `/Contents` non-kosong |
| AC-08 | PDF asli VALID | FR-09 semua field `true` |
| AC-09 | PDF tampered INVALID | ubah 1 byte di luar `/Contents` → `documentIntegrity:false`, `signatureValid:false`, HTTP tetap `200` |
| AC-10 | Wrong public key INVALID | verifikasi dengan key lain → `signatureValid:false`, `publicKeyMatch:false` |
| AC-11 | Token QR salah/tak terdaftar | `tokenValid:false`, HTTP `200` (bukan 404) |
| AC-12 | Benchmark signing | jalankan 30× operasi sign, catat `n, min, max, mean, median, stddev` pakai `time.perf_counter_ns()` |
| AC-13 | Benchmark verification | sama seperti AC-12 untuk operasi verify |
| AC-14 | Ukuran signature terdokumentasi | catat dan simpan: ukuran raw RSA-PSS signature (byte), ukuran public key DER/PEM (byte), ukuran penuh `/Contents` (byte) — tiga angka terpisah, jangan digabung |

Test tambahan wajib (bukan bagian AC tapi WAJIB lulus sebelum Definition of Done):
- Signature dari `privateKeyA` diverifikasi dengan `publicKeyB` (bukan pasangannya) → harus `INVALID`.
- Token diganti karakter acak yang valid base64url tapi tidak pernah di-generate sistem → `tokenValid:false`.

---

## 14. Urutan Implementasi (WAJIB diikuti berurutan, jangan lompat)

```
1. Eksekusi §4.2 Tahap 0 apa adanya (bukan asumsi bebas): buat repo, jalankan `create-next-app` untuk `apps/web`, init Prisma di root, buat venv + install dependency FastAPI di `services/signer`, hasil akhir harus cocok persis dengan §4.1
2. Setup Supabase project (aktifkan Google OAuth provider di dashboard) + setup Prisma (`prisma init`, isi `DATABASE_URL`/`DIRECT_URL`) + `prisma migrate dev` untuk skema §6 + tambahkan partial unique index manual (§6) + terapkan `supabase/policies.sql` (RLS, defense-in-depth)
3. Implement FR-01 Authentication (Google OAuth via Supabase Auth + route `/auth/callback` + upsert `profiles` via Prisma)
4. Implement tabel documents + FR-04 PDF upload + R2 integration
5. Implement FR-02 + FR-03 (RSA key generation + AES-256-GCM encryption)
6. Implement raw RSA-PSS sign/verify di services/signer (unit test dulu, tanpa PDF)
7. Implement PDF signing service dengan pyHanko (FR-08)
8. Implement signature appearance (FR-06)
9. Implement QR generation (FR-07)
10. Implement verification endpoint (FR-09) + self-verification (§12 langkah 11-13)
11. Implement tamper detection test (FR-10 / AC-09)
12. Implement wrong-key detection test (FR-11 / AC-10)
13. Implement forged/unknown token test (FR-12 / AC-11)
14. Implement benchmark script (AC-12, AC-13, AC-14)
15. Deploy web ke Vercel, signing service ke Render (env terpisah dev/prod, §5)
16. Jalankan seluruh test §13, pastikan semua lulus
```

DILARANG mengerjakan fitur di luar daftar ini (multi-signer, blockchain, ECDSA/ML-DSA, dsb.) sebelum langkah 1–16 di atas seluruhnya lulus test.

---

## 15. Non-Functional Requirements (Angka Final)

| Aspek | Target |
|---|---|
| SHA-256 pada PDF ≤5 halaman & ≤2MB | < 100 ms |
| RSA-PSS raw signing | < 100 ms |
| RSA-PSS raw verification | < 100 ms |
| QR generation | < 100 ms |
| Full PDF signing (≤5 halaman, ≤2MB) | < 3 detik |
| Full PDF verification (≤5 halaman, ≤2MB) | < 3 detik |

Reliability (WAJIB):
- PDF gagal parse → reject sebelum masuk pipeline signing.
- Upload ke R2 gagal → retry (maks 3x, exponential backoff).
- Signing service tidak dapat dihubungi/timeout → `502 SIGNING_SERVICE_UNAVAILABLE`, status dokumen tetap `SIGNING` (bukan `SIGNED`/`INVALID`), boleh di-retry user.
- DILARANG set `documents.status = 'SIGNED'` sebelum self-verification (§12 langkah 11) sukses.

Observability (WAJIB): setiap request signing/verifikasi log terstruktur JSON berisi `requestId`, `documentId`, `signatureId` (bila ada), `event`, `durationMs`, `status`.

---

## 16. Definition of Done (MVP)

MVP dianggap selesai HANYA jika seluruh berikut benar:
1. Semua FR-01 s.d. FR-12 diimplementasikan sesuai §7.
2. Semua AC-01 s.d. AC-14 di §13 lulus sebagai automated test, bukan manual check.
3. Test tambahan wrong-key dan forged-token (§13) lulus.
4. `git grep` untuk private key plaintext = 0 hasil (AC-04).
5. Web ter-deploy di Vercel, signing service ter-deploy di Render, keduanya bisa saling terhubung dengan env production terpisah dari dev.
6. Benchmark 30× signing dan 30× verification tersimpan sebagai laporan (tabel `n, mean, median, min, max, stddev`).

---

## 17. Non-Goals (DILARANG diimplementasikan di MVP)

PSrE/sertifikat elektronik resmi, OCSP/CRL, Trusted Timestamp Authority resmi, identitas biometrik, notifikasi WhatsApp, email production, multi-signer kompleks, blockchain sebagai timestamp, ECDSA/ML-DSA. Semua ini hanya boleh masuk roadmap terpisah setelah §16 terpenuhi, dan HANYA jika pengguna meminta eksplisit.
