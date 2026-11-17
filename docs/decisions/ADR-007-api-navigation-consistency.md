# ADR-007: Kategoriya response va Back navigatsiyasi

- **Status:** Accepted for MVP v1.1
- **Decision date:** 2026-10-12

## Context

Category products endpointining array response'i sahifadagi category sarlavhasini mustaqil bermas edi. Bosh kategoriyalar sahifasi uchun o‘ziga qaytaruvchi Back tugmasi ham noaniq bo‘lgan.

## Decision

`GET /api/v1/categories/{category_slug}/products/` response: `{"category": {"id": ..., "name": ..., "slug": ...}, "products": [...]}`. Product detail va Favorites item category slugni beradi. Site Back parent URLga yuradi, browser Back browser tarixiga tayanadi. Bosh sahifada back-to-self qo‘yilmaydi, sayt yangi tabni majburan yopmaydi.

## Consequences

- Kategoriya sarlavhasi uchun qo‘shimcha API so‘rovi kerak emas.
- API arraydan object responsega o‘zgardi; frontend v1.1ga mos bo‘lishi kerak.
- Deep link'da ham product detail sahifasidan parent categoryga qaytish ishlaydi.
