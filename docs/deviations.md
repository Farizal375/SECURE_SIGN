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

## DEV-007: PRD-UI §11a pending (frontend)
- **PRD Requirement**: Answer all §11a questions before implementing steps 4+ of PRD-UI §16.
- **Actual**: Frontend stopped at PRD-UI §16 step 3 (setup tokens, login, auth callback, AppShell, middleware complete; `tsc --noEmit` and `eslint` pass).
- **Reason**: §11a questions not yet answered by user.
- **Impact**: `documents/new`, `dashboard/`, `documents/`, `documents/[id]`, `sign/[signingRequestId]`, PDF source URL, uploadUrl mechanism, signed-PDF download remain blocked or empty-state until answers are recorded here.
