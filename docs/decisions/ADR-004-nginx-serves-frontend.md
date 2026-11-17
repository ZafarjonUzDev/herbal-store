# ADR-004: Nginx frontend fayllarini ham beradi

- **Status:** Accepted for MVP
- **Decision date:** 2026-10-12

## Context

Frontend HTML/CSS/Vanilla JS bo‘lib, alohida Node.js server/build pipeline talab qilmaydi.

## Decision

Nginx image frontend assetlarini o‘z ichiga oladi. Nginx `/api/` va `/admin/`ni Django/Gunicorn'ga proxy qiladi; `/static/` va `/media/` fayllarini mos volume'dan serve qiladi.

## Consequences

- Alohida frontend container yoki Node.js runtime yo‘q.
- Frontend/backend same-origin bo‘ladi va CORS sozlamalariga ehtiyoj kamayadi.
- Frontend assetlari o‘zgarganda Nginx image rebuild/redeploy qilinadi.
