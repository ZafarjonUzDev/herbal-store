# 11 — Implementation Plan (Architecture → Code)

Bu reja bir kun ichida mukammal production sistemaga kafolat bermaydi. Maqsad — scope'ni muzlatib, implementatsiya xavfini kamaytirish va har bir bosqichni tekshirish.

## Phase 0 — Repository va docs

- Ushbu arxitektura hujjatlarini repository'ga ko‘chirish.
- `AGENTS.md`, `.gitignore`, root `.env.example` va README'ni tekshirish.
- Faqat zarur project directories yaratish.

Exit criteria: talablar va API kontrakti bitta versiyada; scope kengaytirilmagan.

## Phase 1 — Django skeleton va configuration

- Virtual/Docker build muhiti va Django project yaratish.
- Custom `accounts.User`ni birinchi migrationdan oldin e’lon qilish.
- Environment settings, PostgreSQL connection va root URL'lar.
- DRF, JWT, OpenAPI packages.

Exit criteria: app ishga tushadi, DB ulanadi, migrations ishlaydi.

## Phase 2 — Catalog + Admin

- Category/Product models, constraints va migrations.
- Django Admin customization.
- Public serializers/views/URLs.
- Media image upload va detail response.

Exit criteria: kategoriya/product admin CRUD; public GET endpoint testlari.

## Phase 3 — Accounts + JWT

- Registration serializer/view. Auth view CSRF protectionni `enforce_csrf_checks=True` testlar bilan tasdiqlash.
- Login, refresh-cookie, CSRF, logout flow.
- Token lifetimes, rotation/blacklisting, throttling.

Exit criteria: browser va API-client orqali auth flow testlari.

## Phase 4 — Favorites

- SavedProduct model/unique constraint.
- Save/list/delete endpointlari.
- User ownership va duplicate behavior.

Exit criteria: auth/authorization testlari o‘tadi.

## Phase 5 — Frontend

- Common CSS, API client, auth client.
- Category → products → product detail.
- Registration/login.
- Pending save flow (guest va oldingi akkauntli user uchun); silent refresh va pending state cancel semantics.
- Favorites list/remove.
- Loading/error/empty states, Back button behavior.

Exit criteria: asosiy browser user flow boshidan oxirigacha ishlaydi.

## Phase 6 — Docker + Nginx

- Backend image, Nginx image/config, Compose dev/prod.
- Networks, volumes, healthchecks, port exposure.
- Static/media routing.

Exit criteria: fresh environmentda Compose orqali ishlaydi.

## Phase 7 — Quality gates

- Automated tests.
- Migration check.
- Production settings audit.
- `collectstatic`, image build va local production-like smoke test.
- Backup/restore sinovi.

Exit criteria: testlar o‘tgan, release checklist to‘ldirilgan.

## Phase 8 — AWS EC2 deployment

- AWS account/Free Tier eligibility and cost review.
- EC2, Security Group, SSH.
- Docker/Compose, environment secrets, deployment.
- DNS, HTTP-only certificate bootstrap, HTTPS va renewal/reload.
- Production smoke tests.

Exit criteria: sayt HTTPS ostida ishlaydi, public API va admin ochiladi, Favorites/Auth ishlaydi, backup amali hujjatlashtirilgan.

## Codex bilan ishlash qoidasi

Bir promptda butun loyihani yozdirma. Har phase uchun alohida vazifa ber, `AGENTS.md`ni o‘qishini ayt, o‘zgarishlarni review qil, testni qayta bajar va faqat so‘ng keyingi phase'ga o‘t.
