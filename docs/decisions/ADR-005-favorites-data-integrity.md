# ADR-005: Favorites Product ma’lumotini nusxalamaydi

- **Status:** Accepted for MVP
- **Decision date:** 2026-10-12

## Context

User mahsulotni saqlaydi, lekin admin narx, rasm, availability va tavsifni keyinchalik o‘zgartirishi mumkin.

## Decision

`SavedProduct` faqat `user`, `product`, `created_at` relationini saqlaydi. `(user, product)` unique constraint bor. Product o‘chirilsa SavedProduct relationlari CASCADE bilan o‘chadi; Product vaqtincha sotuvda bo‘lmasa (`is_available=False`), saved relation qoladi.

Category mahsulotli bo‘lsa `PROTECT` bilan o‘chirishga ruxsat berilmaydi.

## Consequences

- Favorites har doim Productning joriy ma’lumotini ko‘rsatadi.
- Product o‘chirilganda bookmarkning o‘zi ham o‘chadi.
- Categoryni olib tashlashdan oldin uning mahsulotlari ko‘chirilishi yoki o‘chirilishi kerak.
