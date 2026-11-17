# ADR-003: JWT customer Favorites uchun

- **Status:** Accepted for MVP
- **Decision date:** 2026-10-12

## Context

Katalog public bo‘lishi kerak. Saqlangan mahsulotlar esa userga xos va faqat o‘sha userga ochiq bo‘lishi kerak. Kurs talabi JWT auth ishlatishni talab qiladi.

## Decision

Public category/product GET endpointlari anonymous foydalanishga ochiq. Registration/login JWT access/refresh token chiqaradi. JWT faqat Favorites kabi protected customer API'larni himoya qiladi. Django Admin o‘zining session authenticationidan foydalanadi.

Access JWT JavaScript memoryda saqlanadi; refresh JWT HttpOnly cookie'da. Cookie-based refresh/logout va cookie o‘rnatuvchi auth flow'lar CSRF/Origin himoyasi bilan ishlaydi.

## Consequences

- JWT haqiqiy biznes funksiyasiga xizmat qiladi.
- Token lifecycle oddiy bare-JWT'dan murakkabroq; custom cookie refresh view'lari va testlar kerak.
- Multi-page frontend har bir protected page load paytida zarurat bo‘lsa refresh qiladi.
