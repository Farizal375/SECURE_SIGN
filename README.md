# SecureSign

Aplikasi web digital signature dua-layanan:
- **apps/web**: Next.js 15 (App Router, TypeScript, Tailwind CSS, shadcn/ui)
- **services/signer**: FastAPI (Python) — signing & verification service

## Setup Lokal

### Web
`ash
cd apps/web
npm install
npm run dev
`

### Signing Service
`ash
cd services/signer
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
`

## Environment Variables
Lihat .env.example untuk daftar lengkap variabel yang diperlukan.
