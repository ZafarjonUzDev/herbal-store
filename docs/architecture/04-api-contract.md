# 04 — API Contract v1.1

## UZ/RU qo‘shimcha kontrakti — 2026-11-03

- Parametrsiz barcha mavjud endpointlar avvalgi UZ response shaklini saqlaydi.
- Catalog va Favorites GET: `?lang=uz` yoki `?lang=ru`. Boshqa qiymat → 400.
- Explicit til uchun Category, Product va nested category obyektlari `language`
  va `translation_available` qaytaradi. RU mavjud bo‘lmasa tarjima qilinadigan
  `name`, `description`, `detailed_information` (javobda mavjudlari) `null` bo‘ladi.
  UZ kontent ruscha o‘rnida berilmaydi; category holati productdan mustaqil.
- `id`, `slug`, `image`, `price`, `is_available`, `saved_at` va barcha Favorites
  munosabatlari tilga umumiy. Parametrsiz exact-key kontrakti o‘zgarmaydi.
- `Content-Language` tanlangan tilni bildiradi; default UZ, `Accept-Language`
  parametr o‘rnini bosmaydi. Tartiblash va `no-store` avvalgidek.
- Endpointlar/auth/CSRF/Origin/201–200/ownership qoidalari o‘zgarmaydi.

Masalan, `GET /api/v1/products/eski-slug/?lang=ru` uchun RU yo‘q bo‘lsa:
`{"id": 10, "slug": "eski-slug", "name": null, "description": null,
"detailed_information": null, "language": "ru", "translation_available": false,
...}`. Schema nullable text va til parametrini hujjatlashtiradi.

## 1. Umumiy qoidalar

- API root: `/api/v1/`
- JSON request/response; image URL'lari string bo‘ladi.
- Public catalog endpointlari `AllowAny` va faqat read-only.
- Favorites endpointlari `IsAuthenticated` va current user bilan scope qilinadi.
- MVPda pagination yo‘q: Category list va Favorites list JSON array qaytaradi; Category Products esa category metadata va `products` arrayini bir JSON objectda qaytaradi. Katalog hajmi oshsa pagination kontrakt o‘zgarishi sifatida qayta ko‘riladi.
- API listlari tartibi aniq: Category va Product `name,id` bo‘yicha, Favorites `-created_at,-id` bo‘yicha.
- Public katalog JSON javoblari dastlab `Cache-Control: no-store` bilan chiqariladi: admin o‘zgartirgan qiymatlar keyingi requestda ko‘rinishi kerak. Real-time push talab qilinmaydi.
- Public API'dan product/category CRUD mavjud emas.
- DRF/OpenAPI schema: `/api/schema/`; Swagger UI: `/api/docs/` (productionda public ko‘rsatish siyosatini deploymentda belgilang).

## 2. Endpoint xaritasi

| # | Method | Endpoint | Auth | Vazifa |
|---|---|---|---|---|
| 1 | GET | `/api/v1/categories/` | Public | Barcha kategoriyalar |
| 2 | GET | `/api/v1/categories/{category_slug}/products/` | Public | Category mahsulotlari |
| 3 | GET | `/api/v1/products/{product_slug}/` | Public | Product detail |
| 4 | GET | `/api/v1/auth/csrf/` | Public | CSRF token olish |
| 5 | POST | `/api/v1/auth/register/` | Public + CSRF | User yaratish va login holatini boshlash |
| 6 | POST | `/api/v1/auth/token/` | Public + CSRF | Login |
| 7 | POST | `/api/v1/auth/token/refresh/` | Refresh cookie + CSRF | Yangi access token; refresh rotation bo‘lsa cookie ham yangilanadi |
| 8 | POST | `/api/v1/auth/logout/` | Refresh cookie + CSRF | Refresh tokenni bekor qilish va cookie'ni tozalash |
| 9 | GET | `/api/v1/me/saved-products/` | JWT | O‘z saved productlarini ko‘rish |
| 10 | POST | `/api/v1/me/saved-products/` | JWT | Productni saqlash |
| 11 | DELETE | `/api/v1/me/saved-products/{product_id}/` | JWT | O‘z saved relationini o‘chirish |

Django Admin `/admin/` ostida va public catalog API'dan alohida ishlaydi.

## 3. Category list

`GET /api/v1/categories/`

Response `200 OK`:

```json
[
  {"id": 1, "name": "Dorivor giyohlar", "slug": "dorivor-giyohlar"},
  {"id": 2, "name": "Tabiiy mahsulotlar", "slug": "tabiiy-mahsulotlar"}
]
```

Category response ichki timestamp yoki admin fieldlarini chiqarmaydi.

## 4. Category products

`GET /api/v1/categories/{category_slug}/products/`

Response `200 OK`:

```json
{
  "category": {
    "id": 1,
    "name": "Dorivor giyohlar",
    "slug": "dorivor-giyohlar"
  },
  "products": [
    {
      "id": 10,
      "name": "Moychechak",
      "slug": "moychechak",
      "image": "https://example.uz/media/products/moychechak.jpg",
      "price": "35000.00",
      "is_available": true
    }
  ]
}
```

Kategoriya sahifasi title'ini olish uchun alohida GET shart emas. Agar category mavjud, ammo mahsuloti yo‘q bo‘lsa `200` va `"products": []`. Category mavjud bo‘lmasa `404`.

## 5. Product detail

`GET /api/v1/products/{product_slug}/`

Response `200 OK`:

```json
{
  "id": 10,
  "name": "Moychechak",
  "slug": "moychechak",
  "category": {"name": "Dorivor giyohlar", "slug": "dorivor-giyohlar"},
  "image": "https://example.uz/media/products/moychechak.jpg",
  "price": "35000.00",
  "is_available": true,
  "description": "Mahsulot haqida qisqa tavsif.",
  "detailed_information": "Do‘kon tasdiqlagan batafsil ma’lumot."
}
```

`category.slug` detaildagi sayt Back tugmasi to‘g‘ri category mahsulotlariga qaytishi uchun ham ishlatiladi.

## 6. Registration

`POST /api/v1/auth/register/`

Request:

```json
{"username": "zafarjon", "password": "a-strong-user-chosen-password"}
```

Muvaffaqiyat: `201 Created`; body:

```json
{"user": {"id": 25, "username": "zafarjon"}, "access": "<access-jwt>"}
```

Refresh token bodyga yozilmaydi; u HttpOnly cookie orqali beriladi. Frontend CSRF tokenini header orqali yuboradi. Registrationning o‘zi Favorites yaratmaydi.

Xatolar: invalid data uchun `400`; username band bo‘lsa username field validation xatosi.

## 7. Login

`POST /api/v1/auth/token/`

Request:

```json
{"username": "zafarjon", "password": "..."}
```

Muvaffaqiyat `200 OK`:

```json
{"access": "<access-jwt>"}
```

Refresh token HttpOnly cookie'da. Noto‘g‘ri credential uchun `401` va username mavjudligini oshkor qilmaydigan umumiy xabar.

## 8. CSRF, refresh, logout

`GET /api/v1/auth/csrf/` → `200 {"csrfToken": "..."}` va CSRF cookie'ni o‘rnatadi/yangilaydi. Bu endpoint refresh cookie qiymatini JSONda bermaydi.

Frontend `POST /register/`, `/token/`, `/token/refresh/`, `/logout/` so‘rovlarida `X-CSRFToken` headerini yuboradi. Backend mos Origin/CSRF siyosatini qo‘llaydi. DRF `APIView`ning default CSRF xulqiga ko‘r-ko‘rona suyanilmaydi: token cookie bilan ishlaydigan barcha auth POST endpointlarida aniq `csrf_protect` yoki ekvivalent tekshiruv sozlanadi; `enforce_csrf_checks=True` bilan rad etish holatlari test qilinadi.

`POST /api/v1/auth/token/refresh/`: refresh JWT bodydan emas, HttpOnly cookie'dan olinadi. `200 {"access": "<new-access-jwt>"}`; refresh rotation yoqilgan bo‘lsa yangi refresh cookie o‘rnatiladi.

`POST /api/v1/auth/logout/`: cookie ichidagi yaroqli refresh token blacklist qilinadi va cookie expire qilinadi. Cookie yo‘q yoki eskirgan bo‘lsa ham tozalashga urinish `204 No Content` qaytaradi. O‘g‘irlangan **access** token darhol bekor bo‘lmaydi: u muddati tugaguncha ishlashi mumkin; odatdagi browser logout esa xotiradagi access tokenni o‘chiradi. Muvaffaqiyat `204 No Content`.

## 9. Favorites list

`GET /api/v1/me/saved-products/`

Header: `Authorization: Bearer <access-token>`.

Response `200 OK` — product detailga mos soddalashtirilgan array:

```json
[
  {
    "id": 10,
    "name": "Moychechak",
    "slug": "moychechak",
    "category": {"name": "Dorivor giyohlar", "slug": "dorivor-giyohlar"},
    "image": "https://example.uz/media/products/moychechak.jpg",
    "price": "35000.00",
    "is_available": true,
    "saved_at": "2026-10-12T10:30:00+05:00"
  }
]
```

Bu endpoint faqat `request.user`ga tegishli SavedProduct'larni qaytaradi; Productning joriy ma’lumotlari o‘qiladi.

## 10. Save product

`POST /api/v1/me/saved-products/`

Request:

```json
{"product_id": 10}
```

Birinchi muvaffaqiyatli saqlash: `201 Created`:

```json
{"product_id": 10, "message": "Mahsulot saqlandi."}
```

Agar ayni user bu mahsulotni oldin saqlagan bo‘lsa, duplicate yozuv yaratilmaydi; idempotent UI uchun `200 OK` va `{"product_id": 10, "message": "Mahsulot avval saqlangan."}` qaytariladi. Database unique constraint poyga holatini ham himoya qiladi.

Yuborilgan `product_id` turi noto‘g‘ri yoki product mavjud bo‘lmasa `400` va `product_id` field xatosi qaytariladi; shu siyosat v1.1 uchun qat’iy. Product `is_available=false` bo‘lsa ham saqlashga ruxsat. Parallel requestlarda unique constraint buzilishi `500`ga aylanmasin: `get_or_create`/yaxlit tranzaksiya va takroriy holatni izchil `200`ga qaytarish test qilinsin.

## 11. Delete saved product

`DELETE /api/v1/me/saved-products/{product_id}/`

Muvaffaqiyat: `204 No Content`. Object lookup joriy user bilan cheklanadi; boshqa userning product relationini o‘chirishga yo‘l yo‘q. Relation joriy user uchun topilmasa `404`.

## 12. Umumiy status code

- `200`: GET muvaffaqiyatli, yoki avval saqlangan product qayta so‘ralgan
- `201`: registration yoki yangi SavedProduct yaratildi
- `204`: logout yoki delete muvaffaqiyatli
- `400`: request/serializer validation xatosi
- `401`: JWT yo‘q, noto‘g‘ri yoki muddati tugagan va refresh qilinmagan
- `403`: autentifikatsiyalangan userda tegishli ruxsat yo‘q yoki CSRF/Origin tekshiruvi rad etildi
- `404`: resource mavjud emas yoki current user scope'ida topilmadi
- `429`: rate limit
- `500`: faqat umumiy xato; stack trace clientga qaytarilmaydi

## 13. Authorization va refresh boshlash talqini

- To‘liq sahifa navigationi access tokenning JS memory holatini yo‘qotadi. `Saqlash` yoki protected sahifa ochilganda frontend guest deb hukm qilishdan oldin cookie asosidagi **ixtiyoriy refresh**ni sinaydi.
- Refresh muvaffaqiyatli bo‘lsa, mavjud userdan registration so‘ralmaydi. Refresh bo‘lmasa/yaroqsiz bo‘lsa, registration sahifasi login yo‘li bilan ochiladi. Login/registration muvaffaqiyatidan keyin pending Save bajariladi.
- Delete yo‘li joriy userga tegishli bo‘lmagan relation uchun ham `404` qaytaradi.
- Barcha image URLlar request originida to‘liq HTTPS URL sifatida qaytadi.

## 14. API versiyasi va pagination

`/api/v1/` versiya prefiksi saqlanadi. v1 MVP ro‘yxatlarida pagination yo‘q, chunki scope va katalog hajmi kichik deb taxmin qilinadi. Real ma’lumot hajmi o‘sganda pagination qo‘shishdan oldin response contract va frontend yangilanadi.
