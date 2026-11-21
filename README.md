# Herbal Store — Dorivor giyohlar katalogi va axborot portali (MVP)

> **Holat:** Production deploy uchun tayyorlangan (`Docker`, `PostgreSQL`, `Nginx`, `Django/DRF`, `JWT`, `Swagger`).  
> **Live Demo:** *(3–4-bosqichda AWS EC2 server havolasi qo‘yiladi)*  
> **API Docs (Swagger UI):** *(3–4-bosqichda `/api/docs/` havolasi qo‘yiladi)*

**Herbal Store** — real dorivor giyohlar do‘koni mijozlari uchun mo‘ljallangan ikki tilli (**UZ / RU**) mahsulotlar katalogi va axborot portali. Tizim foydalanuvchilarga dorivor giyohlarning rasmi, narxi, do‘konda mavjudligi, qisqacha tavsifi va batafsil qo‘llanmasini qulay ko‘rish hamda shaxsiy «Saqlanganlar» ro‘yxatini yuritish imkonini beradi.

> **Biznes-mantiq chegarasi (ADR):** Do‘konning real ish jarayonidan kelib chiqib, e-commerce savatcha, onlayn to‘lov, yetkazib berish va qidiruv modullari MVP tarkibiga ataylab kiritilmagan. Barcha texnik va arxitektura qarorlari [`docs/architecture/`](docs/architecture/) hamda [`docs/decisions/`](docs/decisions/) (ADR-001 — ADR-010) hujjatlarida asoslangan.

---

## Texnologik stek va Arxitektura

Loyiha **Modular Monolith** (`accounts`, `catalog`, `favorites`) arxitekturasida qurilgan bo‘lib, barcha servislar izolyatsiyalangan Docker Compose tarmoqlarida ishlaydi:

- **Backend:** Python 3.13, Django 5.2 LTS, Django REST Framework (DRF), Gunicorn
- **API Hujjatlar:** OpenAPI 3.0 / Swagger UI (`drf-spectacular`)
- **Autentifikatsiya va Xavfsizlik:** SimpleJWT (`HttpOnly` + `SameSite=Strict` refresh cookie, token rotation & blacklist), explicit CSRF/Origin himoyasi, `ScopedRateThrottle` (brute-force himoyasi)
- **Ma’lumotlar bazasi:** PostgreSQL 16 (tashqi porti yopiq ichki `db_network` tarmog‘ida)
- **Web Server va Reverse Proxy:** Nginx (frontend statik fayllari, `/static/` va `/media/` fayllarini to‘g‘ridan-to‘g‘ri tarqatadi; `/api/`, `/admin/` va `/health/` so‘rovlarini backend’ga yo‘naltiradi)
- **Frontend:** HTML5, CSS3 (2–5 ustunli responsive grid), Vanilla JavaScript (ES modules, UZ/RU lokalizatsiya)

### Asosiy funksional imkoniyatlar
- **Ikki tilli interfeys va katalog (UZ / RU):** Django Admin paneli to‘liq o‘zbek tilida; kategoriya va mahsulot formalarida Umumiy / UZ / RU maydonlari mavjud. Saytdagi til tanlovi sahifalar o‘rtasida saqlanadi, API esa `?lang=uz|ru` parametrini qo‘llab-quvvatlaydi ([ADR-010](docs/decisions/ADR-010-uz-ru-localization.md)).
- **Brending konfiguratsiyasi:** Do‘kon nomi va logotipi `frontend/js/config.js` (`siteConfig.name`, `siteConfig.logoUrl`) orqali yagona joydan boshqariladi; logo ko‘rsatilmasa standart barg belgisi ishlaydi.
- **Xavfsiz sessiya va «Saqlanganlar»:** Access JWT faqat JavaScript xotirasida saqlanadi, Refresh JWT esa `HttpOnly` cookie orqali *silent refresh* mexanizmi bilan ishlaydi. Mehmon foydalanuvchi mahsulotni saqlamoqchi bo‘lsa, ro‘yxatdan o‘tish yoki kirishdan so‘ng tanlangan mahsulot avtomatik ravishda «Saqlanganlar» ro‘yxatiga qo‘shiladi.
- **Boshqaruv paneli (Django Admin):** Kategoriyalar, mahsulotlar, narxlar, mavjudlik holati (`is_available`), rasmlar va qo‘llanmalar faqat Admin panel orqali boshqariladi.

---

## Foydalanuvchi oqimi (User Flow)

1. **Katalog:** Bosh sahifada kategoriyalar → tanlangan kategoriya mahsulotlari → mahsulotning batafsil sahifasi (rasm, narx, mavjudlik holati, qisqa tavsif va qo‘llanma).
2. **Saqlash (Bookmark):** Foydalanuvchi «Saqlash» tugmasini bosadi. Agar tizimga kirmagan bo‘lsa, tanlangan mahsulot `sessionStorage` da vaqtincha eslab qolinadi va ro‘yxatdan o‘tish/kirish yakunlangach Favorites API orqali avtomatik saqlanadi.
3. **Shaxsiy ro‘yxat:** «Saqlanganlar» sahifasida foydalanuvchi o‘z ro‘yxatini (Toshkent vaqti bilan saqlangan sanasi ko‘rsatilgan holda) ko‘radi va keraksiz mahsulotni o‘chiradi.
4. **Chiqish:** «Chiqish» tugmasi tasdiqlash modal oynasini ochadi; tasdiqlanganda refresh token serverda blacklist’ga tushiriladi va cookie tozalanadi.

---

## API v1.1 Endpointlari

| Method | Endpoint | Ruxsat | Vazifasi |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/categories/` | Public | Faol kategoriyalar ro‘yxati |
| `GET` | `/api/v1/categories/{slug}/products/` | Public | Kategoriya va uning mahsulotlari |
| `GET` | `/api/v1/products/{slug}/` | Public | Mahsulotning batafsil ma’lumotlari |
| `GET` | `/api/v1/auth/csrf/` | Public | CSRF cookie va `X-CSRFToken` olish |
| `POST` | `/api/v1/auth/register/` | Public + CSRF | Ro‘yxatdan o‘tish (`access` + `HttpOnly` cookie) |
| `POST` | `/api/v1/auth/token/` | Public + CSRF | Tizimga kirish (`access` + `HttpOnly` cookie) |
| `POST` | `/api/v1/auth/token/refresh/` | Cookie + CSRF | Access tokenni yangilash (token rotation) |
| `POST` | `/api/v1/auth/logout/` | Cookie + CSRF | Refresh tokenni blacklist qilish va chiqish |
| `GET`, `POST` | `/api/v1/me/saved-products/` | Bearer JWT | Saqlangan mahsulotlar ro‘yxati / qo‘shish |
| `DELETE` | `/api/v1/me/saved-products/{product_id}/` | Bearer JWT | Mahsulotni saqlanganlardan o‘chirish |

**Status kodlar shartnomasi:** yangi saqlash — `201`, takroriy saqlash (idempotent) — `200`, noto‘g‘ri yoki mavjud bo‘lmagan `product_id` — `400`, begona yoki topilmagan yozuvni o‘chirish — `404`, auth limitidan oshish — `429`.

---

## Lokal muhitda ishga tushirish (Development)

Talablar: **Docker Engine** va **Docker Compose**. Barcha buyruqlar loyiha ildizida (`herbal_store/`) bajariladi:

```bash
# 1. Tasodifiy SECRET_KEY va DB paroli bilan lokal .env faylini yaratish
python3 scripts/init_dev.py

# 2. Konteynerlarni yig‘ish va ishga tushirish
docker compose -f docker-compose.yml -f docker-compose.dev.yml build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --wait

# 3. Demo katalog (3 kategoriya, 6 mahsulot) va dastlabki admin yaratish
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py seed_demo
python3 scripts/provision_dev.py