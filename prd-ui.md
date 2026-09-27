# PRD-UI — SecureSign
## Spesifikasi Frontend Eksekutabel (Companion Document untuk `PRD_md.md`)

Dokumen ini adalah **satu-satunya sumber kebenaran untuk lapisan frontend** (`apps/web`). Dokumen ini **melengkapi**, bukan menggantikan, `PRD_md.md` ("Root PRD"). Semua aturan, skema data, kontrak API, dan alur di Root PRD tetap berlaku penuh. Jika ada pertentangan langsung antara dokumen ini dan Root PRD pada hal di luar UI (skema DB, kriptografi, endpoint), **Root PRD menang**.

Tidak ada bagian naratif untuk pembaca manusia. Setiap baris adalah instruksi eksekusi.

Referensi RFC 2119 sama seperti Root PRD: **WAJIB**, **DILARANG**, **BOLEH**.

---

## 0. Status Dokumen

- Cakupan: `apps/web` saja — routing, komponen, styling, state UI, binding ke API yang **sudah** ada di Root PRD §10.
- Dokumen ini **DILARANG** dipakai untuk mengubah: skema database (§6 Root), kontrak API (§10–§11 Root), alur kriptografi (§8 Root), atau urutan implementasi backend (§14 Root).
- Dokumen ini **menambah** sub-rute di dalam folder yang sudah ditetapkan di §4.1 Root (`(auth)/`, `dashboard/`, `documents/`, `sign/`, `verify/`). Tidak ada folder top-level baru yang ditambahkan.

---

## 1. Aturan Kerja Agent (Frontend, WAJIB dipatuhi sepanjang implementasi)

1. **DILARANG** menebak endpoint, nama field response, atau method HTTP yang tidak tercantum di Root PRD §10/§11 maupun di §11a dokumen ini. Jika sebuah halaman butuh data yang endpoint-nya tidak ada → **berhenti**, tampilkan/catat sebagai blocker, dan ajukan pertanyaan ke pengguna sebelum menulis kode untuk halaman tersebut. Lihat daftar lengkap di §11a — **WAJIB dibaca sebelum memulai §9**.
2. **DILARANG** membuat endpoint `/api/v1/...` baru dari sisi frontend untuk "menutupi" gap di atas. Menambah endpoint adalah perubahan backend dan tunduk pada aturan §2 Root PRD (harus dikonfirmasi pengguna, ditulis di `docs/deviations.md`).
3. **DILARANG** mengubah nilai desain (warna, font, spacing, radius) di luar token yang dikunci di §3–§6 dokumen ini tanpa instruksi eksplisit dari pengguna. Jika sebuah state visual (mis. warna untuk status `REVOKED`) tidak ada di tabel token → berhenti dan tanyakan, jangan menciptakan warna baru sendiri.
4. Semua komponen interaktif (button, form, dropzone, picker) WAJIB mengimplementasikan seluruh state yang didaftarkan di §8 untuk komponen tersebut (idle/loading/empty/error/success/disabled, sesuai yang relevan). Tidak ada komponen yang "selesai" hanya dengan happy-path.
5. Server Component adalah default di App Router. `"use client"` **hanya** dipasang pada komponen yang butuh interaktivitas browser (form input, drag/drop, canvas overlay, `supabase.auth.*` di client). Data-fetching yang memakai Prisma **WAJIB** tetap di server (Route Handler/Server Action/Server Component) sesuai §3 Root PRD — komponen client **DILARANG** memanggil Prisma.
6. Setiap teks yang tampil ke pengguna WAJIB memakai microcopy yang dikunci di §12, atau — bila belum ada di §12 — mengikuti kaidah di §12.0 sebelum menulis teks baru.
7. Ikuti urutan implementasi §16. Jangan mengerjakan halaman tahap N+1 sebelum tahap N lulus test §15.

---

## 2. Prinsip Desain

Subjek produk: dokumen resmi (surat, kontrak) yang ditandatangani secara kriptografis dan diverifikasi lewat QR. Audiens: staf administrasi/penandatangan (role `signer`, `admin_secretary`) yang bekerja dengan dokumen setiap hari, dan publik (`public_verifier`) yang hanya perlu satu jawaban jelas: **valid atau tidak**.

Arah visual: **dokumen & presisi**, bukan "SaaS dashboard generik". Struktur mengandalkan garis pembatas tipis dan tipografi monospace untuk data teknis (hash, fingerprint, token, ID) — bukan kartu-kartu membulat dengan bayangan seragam. Satu aksen warna dipakai secara disiplin untuk aksi utama dan status "valid"; warna lain hanya untuk status semantik (invalid/warning), tidak untuk dekorasi.

Motion minimal: hanya transisi yang merespons aksi pengguna (buka dialog, hasil verifikasi muncul, drag posisi tanda tangan). **DILARANG** animasi fade-slide-up otomatis pada tiap section/card saat halaman dimuat.

---

## 3. Design Tokens — Warna (Terkunci)

| Token | Hex | Pemakaian |
|---|---|---|
| `--paper` | `#FAFAF9` | Background utama aplikasi (light mode, satu-satunya mode — lihat §2.1) |
| `--surface` | `#FFFFFF` | Panel, dialog, input, area PDF viewer |
| `--surface-muted` | `#F1EFEA` | Section sekunder, hover row tabel, skeleton base |
| `--border` | `#E3E0D8` | Semua garis pembatas/divider (pengganti shadow sebagai device struktural utama) |
| `--ink` | `#14181F` | Teks utama, heading |
| `--ink-muted` | `#5B6472` | Teks sekunder, label, placeholder |
| `--accent` | `#233A6B` | Aksi utama (tombol primer, link, focus ring, item nav aktif) — "seal blue" |
| `--accent-hover` | `#1A2C52` | Hover/active state dari `--accent` |
| `--success` | `#1F6D45` | Status `SIGNED`, `documentIntegrity/signatureValid/publicKeyMatch/qrValid: true` |
| `--success-bg` | `#E8F3EC` | Background badge/alert sukses |
| `--error` | `#9A2E2E` | Status `INVALID`, `REVOKED`, field verifikasi `false`, tombol destruktif |
| `--error-bg` | `#F8E9E9` | Background badge/alert error |
| `--warning` | `#96650F` | Status `SIGNING`, `PENDING`, dokumen mendekati `expires_at` |
| `--warning-bg` | `#F5EDDD` | Background badge/alert warning |
| `--info` | `#3E5C87` | Status `UPLOADED`/`READY`, hint netral |

### 3.1 Mode Warna

Dokumen ini **hanya mengunci light mode**. Dark mode **DILARANG** diimplementasikan di MVP kecuali pengguna meminta eksplisit (selaras §17 Root PRD — non-goal by default).

### 3.2 Pemetaan `DocumentStatus` → Warna (Terkunci, DILARANG menambah status baru)

| `DocumentStatus` | Warna badge | Label tampilan |
|---|---|---|
| `DRAFT` | `--ink-muted` di atas `--surface-muted` | "Draf" |
| `UPLOADED` | `--info` di atas biru muda `#E7ECF3` | "Terunggah" |
| `READY` | `--info` di atas biru muda `#E7ECF3` | "Siap ditandatangani" |
| `SIGNING` | `--warning` di atas `--warning-bg` | "Sedang ditandatangani" |
| `SIGNED` | `--success` di atas `--success-bg` | "Ditandatangani" |
| `INVALID` | `--error` di atas `--error-bg` | "Tidak valid" |
| `REVOKED` | `--error` di atas `--error-bg` | "Dicabut" |

---

## 4. Design Tokens — Tipografi (Terkunci)

| Peran | Font family | Fallback stack |
|---|---|---|
| UI & body (default) | IBM Plex Sans | `'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif` |
| Data teknis (hash, fingerprint, token, UUID, timestamp ISO, angka benchmark) | IBM Plex Mono | `'IBM Plex Mono', ui-monospace, 'SFMono-Regular', monospace` |

Alasan pemakaian monospace: field seperti `sourceSha256`, `publicKeyFingerprint`, `verificationUrl`, `documentId` adalah data yang secara fungsional perlu dibedakan karakter demi karakter — bukan pilihan dekoratif.

**DILARANG** menambah font family ketiga. **DILARANG** memakai huruf kapital penuh (all-caps) untuk label — semua label memakai sentence case sesuai teks aslinya (mis. label field tanda tangan di FR-06 Root PRD ditulis persis `"DITANDATANGANI SECARA DIGITAL"` karena itu adalah string terkunci dari Root PRD, bukan gaya label bebas).

### 4.1 Skala Tipografi

| Token | Ukuran / line-height | Weight | Pemakaian |
|---|---|---|---|
| `text-display` | 2.5rem / 1.15 | 600 | Headline halaman login publik saja |
| `text-h1` | 1.75rem / 1.25 | 600 | Judul halaman (`<h1>` tiap route) |
| `text-h2` | 1.375rem / 1.3 | 600 | Judul section dalam halaman |
| `text-h3` | 1.125rem / 1.4 | 600 | Judul card/panel |
| `text-body` | 1rem / 1.5 | 400 | Teks default |
| `text-small` | 0.875rem / 1.5 | 400 | Teks sekunder, caption, helper text |
| `text-label` | 0.75rem / 1.4 | 500 | Label form, label field (sentence case) |
| `text-mono` | 0.8125rem / 1.5 | 400 (IBM Plex Mono) | Hash, fingerprint, token, ID, timestamp mentah |

Lebar baris konten teks (paragraf/body) WAJIB `max-width: 65ch`.

---

## 5. Design Tokens — Spacing, Radius, Shadow, Breakpoint (Terkunci)

- **Spacing scale** (dipakai via Tailwind spacing default, basis 4px): `1=4px, 2=8px, 3=12px, 4=16px, 6=24px, 8=32px, 12=48px, 16=64px`. **DILARANG** memakai nilai spacing arbitrer di luar skala ini (mis. `p-[13px]`) kecuali untuk alignment presisi overlay `SignaturePositionPicker` (§8.6) yang memang butuh koordinat piksel bebas.
- **Radius**: `radius-sm = 6px` (button, input, badge), `radius-md = 10px` (card, panel, dialog), `radius-none = 0` (frame PDF viewer — meniru tepi kertas fisik, pilihan sengaja, bukan default).
- **Shadow**: dipakai **hanya** untuk elemen mengambang (dialog, dropdown, toast, popover). Elemen statis (card, panel, table) **WAJIB** memakai `border: 1px solid var(--border)`, **DILARANG** memakai shadow sebagai pengganti border.
  - `shadow-float`: `0 4px 16px rgba(20,24,31,0.12)`
  - `shadow-hairline` (opsional, untuk sticky header saat scroll): `0 1px 2px rgba(20,24,31,0.06)`
- **Breakpoint** (Tailwind default, WAJIB dipakai apa adanya, DILARANG kustom): `sm=640px, md=768px, lg=1024px, xl=1280px`.
- **Container**: halaman aplikasi (dashboard/documents/sign) `max-width: 1120px`, margin auto, padding horizontal `px-4` mobile / `px-8` di atas `md`. Halaman form/auth/verify publik: `max-width: 480px`, center.
- **Sidebar** (lihat §7.1): lebar tetap `260px` di atas breakpoint `lg`; di bawah `lg` menjadi `Sheet` (drawer) shadcn/ui.

---

## 6. Implementasi Token — Kode Terkunci

Agent WAJIB menyalin nilai berikut persis (tidak menginterpretasi ulang) ke `apps/web/app/globals.css` dan `apps/web/tailwind.config.ts` saat setup shadcn/ui (§4.2 langkah `npx shadcn@latest init` di Root PRD).

### 6.1 `apps/web/app/globals.css` (variabel CSS, ditambahkan setelah base shadcn init)

```css
:root {
  --paper: #FAFAF9;
  --surface: #FFFFFF;
  --surface-muted: #F1EFEA;
  --border: #E3E0D8;
  --ink: #14181F;
  --ink-muted: #5B6472;
  --accent: #233A6B;
  --accent-hover: #1A2C52;
  --success: #1F6D45;
  --success-bg: #E8F3EC;
  --error: #9A2E2E;
  --error-bg: #F8E9E9;
  --warning: #96650F;
  --warning-bg: #F5EDDD;
  --info: #3E5C87;

  --radius-sm: 6px;
  --radius-md: 10px;
}

body {
  background-color: var(--paper);
  color: var(--ink);
  font-family: 'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif;
}

.font-mono-data {
  font-family: 'IBM Plex Mono', ui-monospace, 'SFMono-Regular', monospace;
}
```

Import font WAJIB lewat `next/font/google` (bukan `<link>` manual), didaftarkan di `apps/web/app/layout.tsx`:

```ts
import { IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google';

const plexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-sans',
});

const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
});
```

### 6.2 `apps/web/tailwind.config.ts` — perluasan `theme.extend`

```ts
theme: {
  extend: {
    colors: {
      paper: 'var(--paper)',
      surface: 'var(--surface)',
      'surface-muted': 'var(--surface-muted)',
      border: 'var(--border)',
      ink: { DEFAULT: 'var(--ink)', muted: 'var(--ink-muted)' },
      accent: { DEFAULT: 'var(--accent)', hover: 'var(--accent-hover)' },
      success: { DEFAULT: 'var(--success)', bg: 'var(--success-bg)' },
      error: { DEFAULT: 'var(--error)', bg: 'var(--error-bg)' },
      warning: { DEFAULT: 'var(--warning)', bg: 'var(--warning-bg)' },
      info: 'var(--info)',
    },
    fontFamily: {
      sans: ['var(--font-sans)'],
      mono: ['var(--font-mono)'],
    },
    borderRadius: {
      sm: 'var(--radius-sm)',
      md: 'var(--radius-md)',
    },
    boxShadow: {
      float: '0 4px 16px rgba(20,24,31,0.12)',
      hairline: '0 1px 2px rgba(20,24,31,0.06)',
    },
  },
},
```

Nilai di §3–§5 dan kode di §6 ini bersifat final dan mengikat, sama seperti §6 Root PRD mengikat skema database.

---

## 7. Komponen shadcn/ui Terkunci (Daftar Tertutup)

Agent **DILARANG** menambah komponen shadcn/ui di luar daftar berikut tanpa instruksi eksplisit pengguna:

`Button`, `Input`, `Label`, `Textarea`, `Form` (react-hook-form + zod), `Card`, `Table`, `Badge`, `Alert`, `Dialog`, `Sheet`, `Tabs`, `Separator`, `DropdownMenu`, `Avatar`, `Progress`, `Skeleton`, `Tooltip`, `Sonner` (toast).

Validasi form WAJIB memakai `zod` + `react-hook-form` (`@hookform/resolvers/zod`), ditambahkan sebagai dependency eksplisit saat `npm install` — **catat penambahan ini ke `docs/deviations.md`** karena tidak ada di §3 Root PRD.

### 7.1 `AppShell` (custom, membungkus semua route privat: `dashboard/`, `documents/`, `sign/`)

- Server Component. Sidebar kiri (lebar `260px`, di bawah `lg` → `Sheet`) berisi: logo/nama produk teks (bukan gambar), nav item (`Dashboard`, `Dokumen`, `Penandatanganan`), separator, info user (`Avatar` + `fullName` + `role`), tombol keluar.
- Topbar mobile (`< lg`): tombol hamburger membuka `Sheet` sidebar.
- Middleware Next.js (server) WAJIB mengecek session sebelum `AppShell` dirender (§FR-01 Root PRD) — redirect ke `(auth)` bila tidak ada session.
- `AppShell` **DILARANG** dipakai di `verify/` dan `(auth)/` — kedua route itu publik, layout terpisah tanpa sidebar.

---

## 8. Komponen Kustom (Spesifikasi State — WAJIB diimplementasikan lengkap)

### 8.1 `GoogleSignInButton` (`"use client"`)
- Props: tidak ada (statis).
- State: `idle` (tombol aktif) → `loading` (spinner + disabled, saat memanggil `supabase.auth.signInWithOAuth`) → redirect browser (tidak ada state "error" lokal; kegagalan OAuth ditangani Google/Supabase di luar kontrol UI ini).
- Perilaku: memanggil persis `supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: `${NEXT_PUBLIC_SITE_URL}/auth/callback` } })` sesuai FR-01 langkah 1 Root PRD. **DILARANG** menambah provider lain di tombol ini (§FR-01 Root: provider lain "boleh ditambahkan sebagai enhancement", bukan bagian tombol default MVP).

### 8.2 `DocumentUploadDropzone` (`"use client"`)
- State wajib: `idle` (area drop kosong, teks ajakan) → `selected` (nama file + ukuran ditampilkan, tombol "Unggah") → `uploading` (`Progress` bar) → `success` (redirect ke `/documents/[id]`) → `error` (`Alert` variant error, pesan sesuai §10 dokumen ini, tombol "Coba lagi").
- Validasi client-side **sebelum** memanggil API (cepat, bukan pengganti validasi server FR-04): ekstensi `.pdf`, ukuran ≤ nilai `MAX_UPLOAD_SIZE_MB` (diambil dari env public yang di-inject server, **DILARANG** hardcode `10` di komponen — lihat §11a butir 6 untuk cara nilai ini sampai ke client).
- Drag-and-drop WAJIB punya fallback `<input type="file">` yang dapat diakses lewat keyboard (klik/Enter pada area dropzone membuka file picker native).

### 8.3 `DocumentStatusBadge`
- Props: `status: DocumentStatus`.
- Murni presentational, memetakan **persis** tabel §3.2. **DILARANG** menambah status yang tidak ada di enum `DocumentStatus` Root PRD §6.

### 8.4 `PdfViewer` (`"use client"`, dibungkus `react-pdf`)
- State wajib: `loading` (`Skeleton` seukuran halaman A4 proporsional) → `loaded` (render halaman + navigasi halaman: tombol prev/next + input nomor halaman) → `error` (PDF gagal dirender di browser — `Alert` "Dokumen tidak dapat ditampilkan", **bukan** mengklaim dokumen rusak karena itu klaim milik FR-04 backend).
- Sumber file PDF untuk `react-pdf`: lihat gap terbuka §11a butir 3 — **WAJIB dikonfirmasi sebelum implementasi**.

### 8.5 `SignaturePositionPicker` (`"use client"`, overlay di atas `PdfViewer`)
- Fungsi: user menggambar satu kotak persegi di atas render halaman PDF; hasil dikonversi dari koordinat piksel layar ke satuan point PDF (`page`, `x`, `y`, `width`, `height` sesuai FR-05 Root PRD) memakai rasio `scale` dari `react-pdf`.
- State wajib: `empty` (belum ada kotak, instruksi "Gambar area tanda tangan pada dokumen") → `drawing` (drag aktif) → `placed` (kotak final + handle resize di 4 sudut + tombol "Hapus") → `submitting` (saat `POST /api/v1/signing-requests`) → `error`.
- **Aksesibilitas WAJIB**: setelah kotak `placed`, kotak dapat dipindah dengan tombol panah keyboard (nudge 1pt, atau 10pt dengan `Shift`) dan diperbesar/perkecil dengan kombinasi `Shift + panah`, karena interaksi drag-only tidak dapat dioperasikan lewat keyboard.
- Validasi wajib sebelum submit: `width > 0`, `height > 0`, kotak tidak keluar dari batas halaman (sesuai constraint FR-05).

### 8.6 `SignaturePreviewCard`
- Presentational, menampilkan **persis urutan field FR-06 Root PRD**: judul `"DITANDATANGANI SECARA DIGITAL"`, `Nama`, `Jabatan`, `Institusi`, `Tanggal` (format `DD MMMM YYYY`, locale `id-ID`), `Signature ID` (font mono, ditruncate tengah dengan tooltip nilai penuh), placeholder QR (lihat §8.7).
- Dipakai di dua tempat: (a) pratinjau sebelum submit (data dari `profiles` milik user login), (b) hasil akhir di halaman detail dokumen setelah `SIGNED`.

### 8.7 `QrCodeDisplay`
- Props: `verificationUrl: string`.
- Menampilkan QR (di-generate ulang di client dari `verificationUrl` **hanya untuk pratinjau sebelum signing** — QR final yang tertanam di PDF WAJIB berasal dari backend FR-07, **DILARANG** frontend mengirim QR buatan sendiri ke signing service).
- State: `loading` (skeleton kotak) → `ready`.

### 8.8 `VerificationResultPanel`
- Props: response persis schema FR-09 Root PRD (`valid, documentIntegrity, signatureValid, publicKeyMatch, qrValid, signer, signedAt`) **atau** `{ tokenValid: false }` untuk kasus token tidak dikenal (§FR-12).
- **WAJIB** menampilkan checklist 4 baris independen (`documentIntegrity`, `signatureValid`, `publicKeyMatch`, `qrValid`) masing-masing dengan ikon pass/fail sendiri — **DILARANG** menyembunyikan/menyingkat menjadi satu status gabungan saja, karena Root PRD §FR-09 eksplisit melarang short-circuit semua-jadi-false.
- Header ringkasan besar: badge hijau "Dokumen valid" hanya bila `valid === true`, badge merah "Dokumen tidak valid" bila `valid === false`. Kasus `tokenValid === false`: tampilkan pesan netral sesuai §12.3 (tanpa membocorkan apakah token salah format vs tidak terdaftar, sesuai §FR-12).
- `aria-live="polite"` pada container hasil, karena hasil muncul setelah aksi async (upload) tanpa navigasi halaman.

### 8.9 `BenchmarkReportView` — **TIDAK ADA**
Tidak ada UI untuk hasil benchmark (§AC-12–AC-14 Root PRD). `scripts/benchmark.py` menghasilkan laporan di luar `apps/web`; **DILARANG** membuat halaman/komponen frontend untuk menampilkannya di MVP kecuali diminta eksplisit oleh pengguna.

### 8.10 `AuditTrailList` — **TIDAK ADA**
Tidak ada endpoint `/api/v1/...` untuk membaca `audit_logs` di §10 Root PRD. **DILARANG** membangun UI riwayat audit di MVP. Lihat §11a butir 7 bila pengguna ingin menambahkan ini.

---

## 9. Peta Halaman & Routing

Format tiap entri: **Route** → Layout · Komponen kunci · Data source · State wajib · Auth.

### 9.1 `/` atau `(auth)/login` — Login
- Layout: center card, `max-width 480px`, tanpa `AppShell`.
- Komponen: judul (`text-display`) + subjudul 1 kalimat + `GoogleSignInButton`.
- Data source: tidak ada (statis).
- Auth: publik. Jika session sudah ada → redirect server-side ke `/dashboard`.

### 9.2 `auth/callback` — Route Handler (tanpa UI)
- Tidak merender halaman. Sesuai FR-01 langkah 2–5 Root PRD: tukar code → cek/insert `profiles` via Prisma → redirect `/dashboard`.
- Bila `exchangeCodeForSession` gagal → redirect ke `/login?error=auth_failed`, halaman login menampilkan `Alert` error sesuai §12.4.

### 9.3 `dashboard/` — Dashboard
- Layout: `AppShell`.
- Komponen: ringkasan jumlah dokumen per status (`Card` + `DocumentStatusBadge`), tombol utama "Unggah dokumen baru" (→ `documents/new`), daftar dokumen terbaru (maks 5 baris, `Table` ringkas).
- Data source: **BLOCKED** — lihat §11a butir 1. Sebelum endpoint list tersedia, halaman ini WAJIB dirender dengan `empty state` statis ("Belum ada dokumen") dan tombol upload tetap berfungsi.

### 9.4 `documents/` — Daftar Dokumen
- Layout: `AppShell`.
- Komponen: `Table` kolom `originalFilename, status (DocumentStatusBadge), createdAt, aksi`; toolbar dengan tombol "Unggah dokumen baru"; filter status (`Tabs`: Semua/Draf/Siap/Ditandatangani/Tidak valid).
- State wajib: `loading` (`Skeleton` baris tabel ×5) → `empty` (ilustrasi teks "Belum ada dokumen yang diunggah" + CTA) → `loaded` → `error` (gagal fetch).
- Data source: **BLOCKED** — lihat §11a butir 1.

### 9.5 `documents/new` — Unggah Dokumen
- Layout: `AppShell`, container `max-width 640px`.
- Komponen: `DocumentUploadDropzone` (§8.2).
- Alur: `POST /api/v1/documents` (request `{filename}`) → dapat `{documentId, uploadUrl}` → unggah file ke `uploadUrl` → `POST /api/v1/documents/{id}/upload-complete` → redirect `documents/[id]`.
- Mekanisme persis `uploadUrl` (method HTTP, header) **BLOCKED** — lihat §11a butir 6.

### 9.6 `documents/[id]/` — Detail Dokumen
- Layout: `AppShell`, dua kolom di atas `lg` (kiri: `PdfViewer`, kanan: panel info+aksi), satu kolom di bawah `lg` (viewer di atas, panel di bawah).
- Panel kanan berisi: `DocumentStatusBadge`, metadata (`originalFilename, fileSize, sourceSha256` font mono, `createdAt`), dan salah satu dari:
  - Status `READY`/`UPLOADED` → tombol "Tentukan posisi tanda tangan" → membuka `SignaturePositionPicker` di atas `PdfViewer` (inline, bukan route terpisah) → submit memanggil `POST /api/v1/signing-requests`.
  - Status `SIGNING` → indikator progres non-interaktif ("Sedang diproses...").
  - Status `SIGNED` → `SignaturePreviewCard` hasil akhir + tombol "Unduh PDF bertanda tangan".
  - Status `INVALID` → `Alert` error "Penandatanganan gagal" (sesuai §12 langkah 12 Root PRD: dokumen gagal self-verify, **DILARANG** menyimpan/menampilkan PDF hasil).
- Data source dokumen tunggal: **BLOCKED** — lihat §11a butir 2. Sumber file untuk `PdfViewer`: **BLOCKED** — lihat §11a butir 3. Tombol unduh PDF bertanda tangan: **BLOCKED** — lihat §11a butir 7.

### 9.7 `sign/[signingRequestId]/` — Konfirmasi Penandatanganan
- Layout: `AppShell`, container `max-width 720px`.
- Komponen: ringkasan dokumen (nama file, posisi tanda tangan yang dipilih), `SignaturePreviewCard` (pratinjau, §8.6), tombol primer "Tandatangani dokumen" (memanggil `POST /api/v1/signatures` dengan `{signingRequestId}`), tombol sekunder "Batalkan".
- State wajib: `idle` → `submitting` (tombol loading, disabled) → `success` (redirect `documents/[id]`) → `error`:
  - `409 SIGNING_REQUEST_EXPIRED` → pesan §12.5, tombol "Buat ulang permintaan" (kembali ke `documents/[id]`).
  - `502 SIGNING_SERVICE_UNAVAILABLE` → pesan §12.6, tombol "Coba lagi" (dokumen tetap status `SIGNING`, boleh retry sesuai §15 Root PRD Reliability).
- Data untuk mengisi ringkasan halaman ini (detail satu `signingRequest`): **BLOCKED** — lihat §11a butir 5.

### 9.8 `verify/` — Verifikasi via Unggah Langsung
- Layout: publik, tanpa `AppShell`, container `max-width 640px`.
- Komponen: `DocumentUploadDropzone` (varian publik, tanpa auth) → `POST /api/v1/verify` (multipart) → `VerificationResultPanel` (§8.8).
- Rate limit publik 10 req/menit/IP (§10 Root) → bila `429 RATE_LIMITED`, tampilkan pesan §12.7, disable tombol submit sementara.

### 9.9 `verify/[token]/` — Verifikasi via QR
- `GET /verify/{token}` di Root PRD dinyatakan sebagai **halaman HTML**, bukan JSON — route ini **WAJIB** Server Component yang merender halaman upload (sama seperti §9.8), lalu client memanggil `POST /api/v1/verify/{token}`.
- Sama seperti §9.8 ditambah field `tokenValid` di response, ditangani sesuai §8.8.

---

## 10. Pemetaan Error Code → Pesan UI (Bahasa Indonesia, Terkunci)

| HTTP | `error.code` | Pesan UI |
|---|---|---|
| 400 | `VALIDATION_ERROR` | "Data yang dikirim tidak valid. Periksa kembali isian Anda." |
| 413 | `FILE_TOO_LARGE` | "Ukuran file melebihi batas maksimum yang diizinkan." |
| 422 | `PDF_UNREADABLE` | "File tidak dapat dibaca sebagai PDF, atau PDF terkunci kata sandi." |
| 422 | `PDF_TOO_MANY_PAGES` | "Jumlah halaman PDF melebihi batas maksimum yang diizinkan." |
| 401 | `UNAUTHENTICATED` | (redirect ke `/login`, tanpa pesan inline) |
| 403 | — | "Anda tidak memiliki akses ke dokumen ini." |
| 404 | — | "Dokumen tidak ditemukan." |
| 409 | `SIGNING_REQUEST_EXPIRED` | "Permintaan tanda tangan ini sudah kedaluwarsa." |
| 502 | `SIGNING_SERVICE_UNAVAILABLE` | "Layanan penandatanganan sedang tidak tersedia. Coba lagi beberapa saat lagi." |
| 429 | `RATE_LIMITED` | "Terlalu banyak percobaan. Coba lagi dalam satu menit." |

Nilai `MAX_UPLOAD_SIZE_MB` dan `MAX_PDF_PAGES` yang sebenarnya (bukan teks generik) **WAJIB** disisipkan ke pesan `FILE_TOO_LARGE`/`PDF_TOO_MANY_PAGES` bila nilainya tersedia di client (lihat §11a butir 6); bila belum tersedia, pakai teks generik di atas apa adanya.

Pesan error **DILARANG** memakai nada permintaan maaf ("Maaf, terjadi kesalahan...") — langsung nyatakan apa yang terjadi dan (bila ada) langkah berikutnya, sesuai §12.0.

---

## 11a. Pertanyaan Terbuka — WAJIB Dikonfirmasi Pengguna Sebelum Implementasi Terkait

Setiap butir berikut adalah gap kontrak data antara kebutuhan UI (§9) dan §10–§11 Root PRD. Sesuai §1 aturan 1 dokumen ini dan §2 aturan 1 Root PRD: agent **DILARANG** menebak jawabannya. Sebelum mengerjakan halaman yang bergantung pada butir tertentu, agent WAJIB berhenti dan bertanya ke pengguna.

1. **Tidak ada endpoint list dokumen** (`GET /api/v1/documents`) untuk mengisi `dashboard/` dan `documents/`. Dibutuhkan: method, query filter (status/pagination), bentuk response.
2. **Tidak ada endpoint detail satu dokumen** (`GET /api/v1/documents/{id}`) untuk `documents/[id]/`.
3. **Tidak ada endpoint/URL untuk membaca isi file PDF asli** (untuk `PdfViewer` via `react-pdf`, dan untuk mengunduh `signed.pdf`). §5 Root PRD tidak mendefinisikan cara publik/aman membaca objek R2 dari browser.
4. **Tidak ada endpoint daftar signer** untuk mengisi field `signerId` pada `POST /api/v1/signing-requests` — apakah user memilih dirinya sendiri secara default (single-signer per Root PRD §17 non-goal "multi-signer kompleks"), atau tetap perlu dropdown?
5. **Tidak ada endpoint detail satu `signingRequest`** untuk mengisi ringkasan halaman `sign/[signingRequestId]/`.
6. **Format `uploadUrl`** pada response `POST /api/v1/documents` tidak dijelaskan (presigned PUT URL S3-compatible langsung ke R2, atau proxy lewat server Next.js). Juga: bagaimana `MAX_UPLOAD_SIZE_MB`/`MAX_PDF_PAGES` disalurkan ke client untuk validasi sisi UI sebelum upload.
7. **Tidak ada endpoint unduh `signed.pdf`** untuk tombol "Unduh PDF bertanda tangan" di `documents/[id]/`.
8. **Tidak ada spesifikasi UI khusus role `admin_secretary`** — apakah admin melihat dokumen milik semua user, atau UI identik dengan `signer` untuk MVP?

Sampai jawaban tersedia, halaman terkait WAJIB dirender dalam **empty/blocked state** yang jujur (lihat §9.3 sebagai contoh), **DILARANG** memakai data dummy/mock yang terlihat seperti data asli di build final.

---

## 12. Microcopy Terkunci

### 12.0 Kaidah Penulisan (untuk teks yang belum terdaftar di §12.1–§12.7)
- Kalimat aktif, sentence case, tanpa filler ("Silakan", "Mohon maaf").
- Nama aksi konsisten dari tombol → hasil: tombol "Tandatangani dokumen" → toast sukses "Dokumen ditandatangani".
- Sebutkan objek nyata pengguna ("dokumen", "tanda tangan"), bukan istilah sistem ("record", "entity").

### 12.1 Judul Halaman (`<h1>`)
| Route | Judul |
|---|---|
| `(auth)/login` | "Masuk ke SecureSign" |
| `dashboard/` | "Dasbor" |
| `documents/` | "Dokumen" |
| `documents/new` | "Unggah dokumen" |
| `documents/[id]` | (nama file asli, `originalFilename`) |
| `sign/[signingRequestId]` | "Konfirmasi tanda tangan" |
| `verify/`, `verify/[token]` | "Verifikasi dokumen" |

### 12.2 Tombol Utama
`"Masuk dengan Google"` · `"Unggah dokumen baru"` · `"Tentukan posisi tanda tangan"` · `"Tandatangani dokumen"` · `"Batalkan"` · `"Unduh PDF bertanda tangan"` · `"Verifikasi dokumen"` · `"Coba lagi"`

### 12.3 Hasil Verifikasi
- Valid: `"Dokumen valid"`
- Tidak valid: `"Dokumen tidak valid"`
- Token tidak dikenal (`tokenValid:false`): `"Tautan verifikasi ini tidak valid atau sudah tidak berlaku."` (sesuai §FR-12 Root PRD — pesan sama untuk semua kasus token gagal)

### 12.4 Auth
`"Gagal masuk dengan Google. Coba lagi."`

### 12.5 Signing Request Kedaluwarsa
`"Permintaan tanda tangan ini sudah kedaluwarsa. Buat permintaan baru dari halaman dokumen."`

### 12.6 Signing Service Tidak Tersedia
`"Layanan penandatanganan sedang tidak tersedia. Dokumen belum ditandatangani — coba lagi beberapa saat lagi."`

### 12.7 Rate Limit
`"Terlalu banyak percobaan verifikasi. Coba lagi dalam satu menit."`

### 12.8 Empty States
- `documents/` kosong: `"Belum ada dokumen yang diunggah."`
- `dashboard/` kosong: `"Belum ada dokumen. Unggah dokumen pertama Anda untuk mulai menandatangani."`

---

## 12a. Aksesibilitas & Responsif (WAJIB)

1. Kontras warna teks-terhadap-background WAJIB memenuhi WCAG 2.1 AA (rasio ≥4.5:1 untuk teks body, ≥3:1 untuk teks besar/UI komponen). Kombinasi token di §3 sudah memenuhi ini — **DILARANG** menurunkan opacity teks di bawah ambang tersebut.
2. Setiap elemen interaktif WAJIB punya `focus-visible` ring memakai `--accent`, terlihat jelas (bukan `outline: none` tanpa pengganti).
3. `SignaturePositionPicker` WAJIB dapat dioperasikan penuh lewat keyboard (§8.5).
4. Semua `img`/ikon dekoratif WAJIB `aria-hidden="true"`; QR code WAJIB punya teks alternatif yang menjelaskan fungsinya (bukan menyebutkan isi payload).
5. `prefers-reduced-motion: reduce` WAJIB dihormati — transisi non-esensial (hover, dialog open/close) diperpendek/dihilangkan.
6. Layout WAJIB responsif turun sampai lebar viewport `360px` tanpa horizontal scroll pada konten (kecuali `Table` yang boleh scroll horizontal di dalam containernya sendiri).
7. Halaman publik (`verify/*`, `(auth)/login`) WAJIB dapat dipakai tanpa JavaScript untuk konten statis (progressive enhancement dasar Next.js Server Component); interaksi upload tetap butuh JS dan itu diterima.

---

## 13. Struktur Direktori Tambahan `apps/web` (Melengkapi §4.1 Root PRD)

Tidak ada folder top-level baru. Isi di dalam folder yang sudah ada di §4.1 Root PRD:

```text
apps/web/
├── app/
│   ├── (auth)/
│   │   └── login/page.tsx
│   ├── auth/callback/route.ts
│   ├── dashboard/page.tsx
│   ├── documents/
│   │   ├── page.tsx
│   │   ├── new/page.tsx
│   │   └── [id]/page.tsx
│   ├── sign/
│   │   └── [signingRequestId]/page.tsx
│   └── verify/
│       ├── page.tsx
│       └── [token]/page.tsx
├── components/
│   ├── ui/                      # shadcn/ui generated components (§7)
│   ├── app-shell.tsx
│   ├── google-sign-in-button.tsx
│   ├── document-upload-dropzone.tsx
│   ├── document-status-badge.tsx
│   ├── pdf-viewer.tsx
│   ├── signature-position-picker.tsx
│   ├── signature-preview-card.tsx
│   ├── qr-code-display.tsx
│   └── verification-result-panel.tsx
```

---

## 14. Binding Data — Aturan Umum

1. Fetching data via Prisma **WAJIB** hanya di Server Component/Route Handler/Server Action, sesuai §3 Root PRD. Halaman `documents/[id]`, `dashboard/`, dsb. WAJIB Server Component untuk bagian data-fetching-nya; bagian interaktif (`SignaturePositionPicker`, dropzone) tetap Client Component terpisah yang menerima data awal lewat props dari Server Component induknya.
2. Setiap query Prisma yang dipanggil dari route privat WAJIB menyertakan filter `ownerId: session.user.id` sesuai §6 Root PRD — **ini berlaku juga untuk Route Handler yang dibuat untuk mengisi gap §11a**, begitu endpoint tersebut disetujui pengguna.
3. `SIGNER_SERVICE_SECRET`, `PRIVATE_KEY_ENCRYPTION_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, kredensial R2 (§5 Root PRD) **DILARANG** muncul di kode Client Component atau di response API manapun ke browser.

---

## 15. Test Wajib Frontend (Vitest + Playwright)

| ID | Test | Assertion Konkret |
|---|---|---|
| UI-01 | Render token warna | Snapshot `globals.css`/computed style tombol primer memakai `--accent` persis `#233A6B` |
| UI-02 | `GoogleSignInButton` | Klik memanggil `supabase.auth.signInWithOAuth` dengan `provider: 'google'` dan `redirectTo` sesuai `NEXT_PUBLIC_SITE_URL` |
| UI-03 | Middleware auth | Akses `/dashboard` tanpa session → redirect ke `/login` (Playwright, cek URL akhir) |
| UI-04 | `DocumentUploadDropzone` validasi client | Pilih file non-PDF → tombol upload disabled + pesan §10 `VALIDATION_ERROR` muncul, **tanpa** memanggil API |
| UI-05 | `DocumentStatusBadge` | Setiap 7 nilai `DocumentStatus` merender warna & label sesuai tabel §3.2 (parametrized test) |
| UI-06 | `SignaturePositionPicker` keyboard | Kotak `placed` dapat dipindah dengan tombol panah tanpa mouse (Playwright keyboard events) |
| UI-07 | `VerificationResultPanel` independen | Mock response dengan `documentIntegrity:true, signatureValid:false` → kedua baris tampil dengan ikon berbeda, **bukan** keduanya `false` |
| UI-08 | Error mapping | Setiap `error.code` di §10 memicu teks pesan yang sama persis dengan tabel §10 (parametrized test) |
| UI-09 | Rate limit publik | Mock `429 RATE_LIMITED` di `verify/` → tombol submit disabled + pesan §12.7 |
| UI-10 | Responsif sidebar | Viewport `<1024px` → sidebar `AppShell` dirender sebagai `Sheet` tertutup by default (Playwright viewport test) |
| UI-11 | Kontras warna | Automated check (axe-core via Playwright) nol pelanggaran kontras pada halaman `dashboard/`, `documents/[id]`, `verify/` |

---

## 16. Urutan Implementasi Frontend (WAJIB berurutan)

```
1. Setup token (§6): globals.css, tailwind.config.ts, next/font, shadcn init (bagian dari §4.2 Tahap 0 Root PRD).
2. Bangun AppShell + halaman (auth)/login + auth/callback (bergantung pada FR-01 Root PRD backend selesai — §14 langkah 3 Root).
3. Ajukan seluruh pertanyaan §11a ke pengguna sebelum melanjutkan ke langkah 4. Catat jawaban ke docs/deviations.md.
4. Bangun documents/new + DocumentUploadDropzone (bergantung pada FR-04 Root PRD backend selesai — §14 langkah 4 Root).
5. Bangun dashboard/ dan documents/ (list) — dengan endpoint hasil §11a butir 1, atau tetap empty-state bila belum disetujui.
6. Bangun documents/[id]/ + PdfViewer + SignaturePositionPicker (bergantung pada FR-05 Root PRD + jawaban §11a butir 2–3).
7. Bangun sign/[signingRequestId]/ + alur konfirmasi (bergantung pada FR-08 Root PRD backend selesai — §14 langkah 7 Root, + jawaban §11a butir 5).
8. Bangun SignaturePreviewCard + QrCodeDisplay (bergantung pada FR-06/FR-07 Root PRD — §14 langkah 8–9 Root).
9. Bangun verify/ dan verify/[token]/ + VerificationResultPanel (bergantung pada FR-09 Root PRD — §14 langkah 10 Root).
10. Jalankan seluruh test §15, pastikan semua lulus, termasuk axe-core aksesibilitas.
```

**DILARANG** mengerjakan langkah N+1 sebelum langkah N lulus test, dan **DILARANG** mengerjakan langkah frontend yang bergantung pada FR backend yang belum selesai di §14 Root PRD.

---

## 17. Definition of Done (Frontend)

MVP frontend dianggap selesai HANYA jika seluruh berikut benar:
1. Semua halaman §9 diimplementasikan sesuai layout/komponen/state yang dispesifikasikan, ATAU dalam blocked/empty state jujur untuk halaman yang bergantung pada §11a yang belum dijawab.
2. Semua token §3–§6 diterapkan persis, nol nilai warna/font/spacing hardcode di luar token.
3. Semua test UI-01 s.d. UI-11 di §15 lulus sebagai automated test.
4. Nol pelanggaran kontras warna (axe-core) di halaman utama.
5. Semua gap §11a sudah diajukan ke pengguna dan dicatat jawabannya di `docs/deviations.md` — tidak ada gap yang "diselesaikan" dengan asumsi diam-diam.
6. Tidak ada kredensial/secret yang bocor ke bundle client (`next build` + cek `NEXT_PUBLIC_*` hanya berisi variabel yang memang publik sesuai §5 Root PRD).

---

## 18. Non-Goals Frontend (DILARANG diimplementasikan di MVP)

Dark mode, UI riwayat audit (`AuditTrailList`, §8.10), UI laporan benchmark (`BenchmarkReportView`, §8.9), multi-bahasa/i18n switcher, UI role `admin_secretary` yang berbeda dari `signer` (sampai §11a butir 8 dijawab), notifikasi push/real-time (WebSocket/SSE untuk status `SIGNING` — polling manual refresh sudah cukup untuk MVP), tema kustom per-institusi/white-label. Semua ini hanya boleh masuk roadmap terpisah setelah §17 terpenuhi, dan HANYA jika pengguna meminta eksplisit — selaras §17 Root PRD.
