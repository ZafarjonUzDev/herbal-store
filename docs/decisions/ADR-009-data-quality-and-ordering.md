# ADR-009: Narx integrity, mahsulot axboroti va tartiblash

- **Status:** Accepted for MVP v1.1
- **Decision date:** 2026-10-12

## Context

Mahsulot narxini noto‘g‘ri saqlash, bo‘sh yo‘riqnoma yoki turlicha tartiblangan listlar mijozga yomon tajriba beradi. Validatorning o‘zi database cheklovi emas.

## Decision

- Product `price=DecimalField(12,2)`; `MinValueValidator(0)` va `CheckConstraint(price >= 0)`.
- `detailed_information` har bir catalog product uchun required oddiy matn. Yo‘riqnoma bo‘lmasa do‘kon tasdiqlagan batafsil ma’lumot qo‘yiladi.
- Category, category products `name,id`, Favorites `-created_at,-id` bo‘yicha saralanadi.
- Product `is_available=False` bo‘lsa ham ko‘rinadi va favorite sifatida saqlanishi mumkin.
- Catalog JSON dastlab `Cache-Control: no-store`, ya’ni keyingi requestda admin o‘zgarishlari yangidan olinadi; real-time yangilash yo‘q.

## Consequences

- Database model va API testlarida shu qoidalar tekshiriladi.
- Admin barcha Productlar uchun mazmunli tafsilotlarni kiritishi kerak.
