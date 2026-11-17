# ADR-001: Modular Monolith

- **Status:** Accepted for MVP
- **Decision date:** 2026-10-12

## Context

Herbal Store bitta do‘konning public katalogi, foydalanuvchi auth'i va Favorites funksiyasidan iborat. Alohida mustaqil xizmatlar yoki jamoalar hozir mavjud emas.

## Decision

Bitta Django project va bitta PostgreSQL database ichida `accounts`, `catalog`, `favorites` Django app'lari ishlatiladi. Alohida mikroservislar yo‘q.

## Consequences

- Deployment, local development va debugging oddiyroq.
- Modul mas’uliyatlari ajratilgan.
- Kelajakda ehtiyoj bo‘lsa modulni mustaqil service qilish uchun hozircha ortiqcha infra yo‘q.
- Barcha modullar bir deployment va database availability'ga bog‘liq.
