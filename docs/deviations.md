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
