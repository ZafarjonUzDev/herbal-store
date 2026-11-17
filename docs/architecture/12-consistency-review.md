# 12 — Architecture Consistency Review v1.1

**2026-11-03 UZ/RU qo‘shimchasi:** foydalanuvchi so‘roviga muvofiq
[ADR-010](../decisions/ADR-010-uz-ru-localization.md) translation jadvallari,
explicit `lang=uz|ru` API va o‘zbekcha standart Adminni belgilaydi. Parametrsiz
v1.1 javob shakli, ID/slug/Favorites/auth/CSRF qoidalari saqlanadi. Eski matnlar
bilan shu lokalizatsiya tafsilotlari zid bo‘lsa yangilangan API qo‘shimchasi va
ADR-010 ustuvor. AWS/production doirasi ochilmagan.

**Review date:** 2026-10-12  
**Status:** Architecture reviewed v1.1; lokal MVP 2026-10-13da implementatsiya va runtime tekshiruvdan o‘tdi  
**Scope:** Business → DB → API → Auth → Frontend → Backend → Deployment → Testing

## 1. Natija

v1.0 paketdagi 19 ta hujjat o‘qildi. Domen chegaralari saqlandi: `accounts`, `catalog`, `favorites`; 4 ta asosiy domain entity; Django Admin CRUD; 3 ta public catalog GET; JWT himoyalangan Favorites; statik frontend; Nginx + Django + PostgreSQL bitta EC2 serverida.

**O‘zgartirilmagan scope:** buyurtma, savatcha, delivery, to‘lov, branch management, SMS, AI, search, murakkab filtrlash va yangi biznes modul yo‘q.

## 2. Topilgan muammolar va yakuniy qarorlar

| ID | Jiddiylik | Muammo | v1.1 yakuniy qaror |
|---|---|---|---|
| CR-01 | UX | Bosh sahifadagi Back o‘ziga qaytarish ehtimoli | Bosh sahifada site Back self-loop yo‘q; browser history tabiiy; brauzerni majburan yopish mumkin emas |
| CR-02 | API/UI | Category products arrayda category nomi yo‘q | `{"category": {...}, "products": [...]}` object; bitta GET bilan to‘liq UI |
| CR-03 | Data integrity | Faqat `MinValueValidator(0)` DBga to‘g‘ridan-to‘g‘ri salbiy narx yozishni to‘xtatmaydi | `CheckConstraint(price >= 0)` qo‘shildi |
| CR-04 | User flow | Already-registered lekin logged-out user Save bosganda qayta registerga yo‘naltirilishi | Registration sahifasida Login yo‘li; login bo‘lgach ham pending Save yakunlanadi |
| CR-05 | Auth | Multi-page JS memory token sahifa almashganda yo‘qoladi; haqiqiy user guest deb qabul qilinishi mumkin | Save click va protected page uchun `ensureAuthenticated` / silent refresh oldindan |
| CR-06 | CSRF | DRF APIView default himoyasiga ortiqcha suyanish cookie-based endpointlarni ochiq qoldirishi mumkin | Login/register/refresh/logout uchun explicit CSRF enforcement va fail-case testlar |
| CR-07 | JWT | Refresh blacklist logout bilan allaqachon berilgan access token darhol o‘ladi degan noto‘g‘ri tasavvur | Access JWT tabiatan expiry'ga qadar amal qilishi mumkin, JS memory tozalanadi |
| CR-08 | Duplicate/race | Parallel ikki Save DB IntegrityErrorni 500ga aylantirishi mumkin | Unique constraint + controlled get-or-create/idempotent 200 test |
| CR-09 | API predictability | Product not found save error 400 yoki 404 noaniq | Request body `product_id` invalid/not found → 400 field validation |
| CR-10 | Data display | Ordering noaniq | Category/Product `name,id`; Favorites `-created_at,-id` |
| CR-11 | Business quality | Batafsil yo‘riqnoma bo‘sh qolishi mumkinligi business maqsadiga zid | Har bir mahsulot uchun tasdiqlangan `detailed_information` majburiy |
| CR-12 | Caching | Admin narxni o‘zgartirsa browser/cache eski ma’lumotni ko‘rsatishi mumkin | Public katalog JSON `Cache-Control: no-store`; keyingi requestda yangilangan data; realtime yo‘q |
| CR-13 | Deploy | Nginx TLS sertifikat mavjud bo‘lmasdan HTTPS config bilan ishga tushsa xato | HTTP-only bootstrap → Certbot webroot → HTTPS → renew/reload |
| CR-14 | Account naming | Username case handling noaniq | MVPda Django defaultga mos case-sensitive username; API ham shu xulqni saqlaydi |
| CR-15 | Save cancellation | Bekor qilingan auth flow eski productni keyin kutilmaganda saqlashi mumkin | User explicit Bekor/Back bossa pending intent tozalanadi; form validation failed bo‘lsa saqlanadi |

## 3. Qatlamlararo shartnoma (single source of truth)

### Backend source of truth

- `Product` nom, rasm, narx, availability va tafsilotlarning yagona manbasi.
- `SavedProduct` faqat `user`, `product`, `created_at` relationini saqlaydi.
- `Category` o‘chirilishi `PROTECT`; `SavedProduct` product/user o‘chirilsa `CASCADE`.

### API

- Category List → array.
- Category Products → `{category, products}`.
- Product Detail → object, `category.slug` bilan.
- Favorites List → user scoped array, current Product data + `saved_at`.
- Save Product → 201 yangi, 200 oldin mavjud, 400 invalid/missing product.
- Delete relation → 204 own, 404 other/missing.
- Auth refresh response → faqat `access`; refresh JWT faqat HttpOnly cookie.

### Frontend

- Statik sahifalar: `index.html`, `category.html`, `product.html`, `favorites.html`, `login.html`, `register.html`.
- Access JWT faqat JS memory. Auth status noaniq bo‘lganda oldin refresh qilinadi.
- Pending save ID sessionStorage'da, auth tokenlar unda yo‘q.
- `register` va `login` pending save'ni muvaffaqiyatli yakunlaydi; explicit cancel intentni bekor qiladi.
- Site Back: category → index; product → category; browser Back → natural history.

### Infrastructure

- Same-origin frontend/API; Nginx frontend va `/static/`, `/media/`ni beradi, `/api/` va `/admin/`ni backendga proxy qiladi.
- PostgreSQL/Gunicorn hostga public publish qilinmaydi.
- TLS bosqichma-bosqich ishga tushiriladi; backup va media ham alohida saqlanadi.

## 4. Codex uchun implementation quality gates

- [ ] **Models:** initial custom User migration to‘g‘ri, DB CHECK/UNIQUE/PROTECT/CASCADE testlardan o‘tadi.
- [ ] **API:** OpenAPI serializerlari response misollariga mos; 11 endpoint (GET/POST/DELETE method variations bilan) to‘g‘ri ishlaydi.
- [ ] **Auth:** CSRF fail tests, refresh rotation, logout, silent refresh va pending save natijalari isbotlangan.
- [ ] **Frontend:** navigatsiya, direct URL, Back, Save/Registration/Login, Favorites/delete va error state tekshirilgan.
- [ ] **Infra:** Docker Compose dev/prod, HTTPS bootstrap, static/media, yopiq ports, production smoke tests, backup/restore ishlaydi.

## 5. Qasddan qoldirilgan implementatsiya va tashqi qarorlar

Quyidagilar **kod yozishdan oldin konseptual jihatdan yetarlicha aniqlangan**, lekin real muhitda tekshirilishi shart:

- Django/DRF/Simple JWT va PostgreSQLning o‘zaro mos **qo‘llab-quvvatlanadigan aniq versiyalari** (pin qilish).
- AWS akkaunt va Free Tier kredit/limitlari; instance RAM/disk ehtiyoji.
- Haqiqiy domen/DNS, public IP va TLS sertifikat olish.
- Do‘kon tomonidan haqiqiy Product ma’lumotlari, yozma yo‘riqnomalar va mahsulot rasmlarining tekshirilgan manbalari.
- Haqiqiy restore sinovi va production deploy — **hali bajarilmagan**.

## 6. Xulosa

**Architecture consistency status: PASS (document/design level).**  
**Implementation status: LOCAL MVP PASS (2026-10-13); AWS/production PENDING.**
Joriy natijalar: [lokal MVP hisoboti](../implementation/MVP-LOCAL-REPORT.md). Quyidagi dastlabki next-step tavsiyasi review sanasidagi tarixiy reja.  
**Next recommended step:** Phase 0 (repository, docs, `.gitignore`, `.env.example`) → Phase 1 (Django skeleton + custom User first migration). Har fazadan keyin test natijalari va diff ko‘rib chiqiladi.

## 7. Tekshirish uchun rasmiy hujjatlar

- Django DB constraints: https://docs.djangoproject.com/en/5.2/ref/models/constraints/
- Django CSRF protection: https://docs.djangoproject.com/en/5.2/ref/csrf/
- DRF authentication: https://www.django-rest-framework.org/api-guide/authentication/
- Simple JWT settings/rotation: https://django-rest-framework-simplejwt.readthedocs.io/en/stable/settings.html
