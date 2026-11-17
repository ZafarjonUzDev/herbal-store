# 02 — Overall Architecture

## 1. Arxitektura stili

**Modular monolith**: bitta Django project, bitta deployment birligi va bitta PostgreSQL bazasi; biznes vazifalari `accounts`, `catalog`, `favorites` modullariga ajratilgan.

Microservices, alohida frontend framework yoki message broker bu scope uchun asoslanmagan.

## 2. Context diagram

```text
Customer Browser ── HTTPS ──> Nginx ──> Static Frontend
                                  └──> Django + DRF ──> PostgreSQL
Administrator Browser ─ HTTPS ──> Nginx ──> Django Admin ──> PostgreSQL
```

## 3. Container diagram

```text
AWS EC2 / Docker Compose
├── nginx
│   ├── HTML/CSS/JS assets (image ichida)
│   ├── /static/ (shared static volume)
│   ├── /media/ (shared media volume)
│   └── reverse proxy: /api/, /admin/, /health/
├── backend (Gunicorn + Django/DRF)
│   ├── accounts
│   ├── catalog
│   └── favorites
└── db (PostgreSQL)
    └── postgres_data volume
```

## 4. Request flow

1. Browser `https://domain/` orqali Nginxga ulanadi.
2. Nginx frontend sahifasini yoki static/media faylini beradi.
3. `/api/` va `/admin/` so‘rovlari Docker tarmog‘i ichida backendga proxylanadi.
4. Django request validation va permissionsni bajaradi.
5. ORM PostgreSQL bilan ishlaydi.
6. JSON/HTML javobi Nginx orqali browserga qaytadi.

## 5. Trust boundaries

- Public browser → faqat Nginx orqali.
- Internetdan backend Gunicorn portiga bevosita kirish yo‘q.
- Internetdan PostgreSQL portiga kirish yo‘q.
- Frontend DB bilan bevosita gaplashmaydi.
- Customer API va Django Admin alohida auth usullaridan foydalanadi.

## 6. High-level module ownership

- `accounts`: User, registration, login, token issuance/refresh/logout.
- `catalog`: Category/Product, public read-only API, Django Admin CRUD.
- `favorites`: SavedProduct relationship; authenticated user's save/list/delete.

Dependency yo‘nalishi: `favorites` → `accounts.User` va `catalog.Product`. `catalog` hech qachon `favorites`ga bog‘lanmaydi.

## 7. Arxitektura tamoyillari

- Single source of truth: Product ma’lumotining yagona manbasi `Product`.
- Least privilege: user faqat o‘z Favorites ma’lumotiga ega.
- Secure by default: yopiq portlar, secretlar environment orqali, HTTPS productionda.
- Simple first: ORM/DRF native imkoniyatlari yetarli bo‘lsa qo‘shimcha qatlam yaratmaslik.
- Reversible decisions: scope o‘zgarsa ADR bilan qaror qayta ko‘riladi.
