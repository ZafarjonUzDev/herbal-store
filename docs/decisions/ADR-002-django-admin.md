# ADR-002: Katalog CRUD uchun Django Admin

- **Status:** Accepted for MVP
- **Decision date:** 2026-10-12

## Context

Do‘kon administratori Category va Product yozuvlarini boshqarishi kerak, ammo alohida custom admin frontend kurs MVPsi uchun zarur emas.

## Decision

Category/Product CRUD Django Admin orqali bajariladi. Public DRF API faqat catalog read endpointlarini beradi. Customer API'da write endpointlar yo‘q.

## Consequences

- Admin UI ishlab chiqish vaqti kamayadi.
- Django session authentication va staff permissions ishlatiladi.
- Admin customization standart Django Admin imkoniyatlari bilan bajariladi: ro‘yxat/filtr/slug sozlamalari, ModelForm label va yordam matnlari, readonly rasm preview’i, statik preview JS va `admin/base_site.html` orqali CSS. Custom admin panel yoki yangi CRUD API yaratilmaydi.
- Agar kelajakda biznesga custom admin UI kerak bo‘lsa, alohida talab va API dizayni talab qilinadi.

## UI/UX refinement — 2026-11-01

Foydalanuvchi so‘ragan admin qulayligi uchun native form label/help, readonly rasm preview’i, tanlangan lokal fayl preview’i va yengil yashil tema qo‘shildi. Django session auth, staff/model permissionlari, Category/Product CRUD, majburiy yo‘riqnoma va model/migrationlar saqlandi. Admin nomi serverdagi `admin.site` sozlamasida; frontend nom/logo konfiguratsiyasi browser sahifalari uchun xizmat qiladi.
