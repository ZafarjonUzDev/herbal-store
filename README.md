# Herbal Store — lokal MVP

2026-11-03 UZ/RU yangilanishi: standart Django Admin o‘zbekcha; Category/Product
formalarida Umumiy / UZ / RU maydonlari bor. Saytdagi UZ/RU tanlovi sahifalar
orasida saqlanadi; RU katalog matnlari faqat Admin orqali qo‘lda kiritiladi.
Yetishmagan tarjima ochiq ko‘rsatiladi. [Arxitektura qarori](docs/decisions/ADR-010-uz-ru-localization.md)
va [backup hamda noutbuk/Redmi qabul sinovi](docs/implementation/UZ-RU-ACCEPTANCE.md).
[Yakuniy kod/test hisoboti](docs/implementation/UZ-RU-LOCALIZATION-REPORT.md):
107/107 Django va 41/41 frontend regression testi muvaffaqiyatli.
Ruxsatdan keyin backup/restore tekshirildi va amaldagi `catalog.0002` qo‘llandi.
Noutbuk: http://127.0.0.1:8080/ ; joriy Wi-Fi orqali Redmi:
http://10.178.150.236:8080/ . RU mahsulot matnlari Admin orqali qo‘lda kiritiladi.

Amaldagi baza uchun `catalog.0002_catalog_translations`ni qo‘llashdan oldin
tekshirilgan PostgreSQL/media backup va alohida ruxsat kerak. Quyidagi oddiy
startup backend entrypoint orqali avtomatik migratsiya bajaradi; mavjud baza
yangilanishida avval backup rejasiga amal qiling. Dev rejimida source mountlar
yangi kodni darhol ko‘rsatadi; yangi Admin/RU oqimi uchun migratsiya zarur.

Amaldagi bazaga tegmay avtomatik tekshirish:

```bash
.venv/bin/python scripts/check_localization.py --keep-data
.venv/bin/python scripts/check_localization.py --browser --keep-data
```

Bu buyruqlar faqat `/tmp` ichidagi yangi PostgreSQL klasterini ishlatadi.
`--browser` haqiqiy Django API/Admin va Chrome oqimlarini shu test bazasida
tekshiradi; `.env` va `.secrets` ishlatilmaydi. Django/OpenAPI/Chrome paketlari
va lokal PostgreSQL server binarylari mavjud bo‘lishi kerak. Standart API UZ;
`?lang=uz|ru` explicit tanlovda tarjima holati ham qaytadi.

Django Admin, public katalog, username/password JWT autentifikatsiyasi va shaxsiy saqlangan mahsulotlar ishlaydi. Frontend HTML/CSS/Vanilla JS, backend Django/DRF, database PostgreSQL; barchasi izolyatsiyalangan Docker Compose va Nginx orqali ishlaydi.

2026-10-13 tekshiruvi: avvalgi Phase 1–3 kodlari saqlandi; 55 ta mavjud test PostgreSQL’da o‘tgach qolgan MVP yozildi. Yakuniy Django suite **77/77 PASS**, frontend auth/navigation regressionlari **16/16 PASS**. Batafsil natijalar: [lokal MVP hisoboti](docs/implementation/MVP-LOCAL-REPORT.md). [Avvalgi runtime hisobot](docs/implementation/PHASE-1-3-RUNTIME-REPORT.md) tarixiy holat va tuzatishlarni saqlaydi.

## Ishga tushirish

Docker Engine va Compose kerak. Buyruqlar loyiha rootida bajariladi:

```bash
python3 scripts/init_dev.py
COMPOSE_BAKE=false docker compose -f docker-compose.yml -f docker-compose.dev.yml build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-build --wait
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py seed_demo
python3 scripts/provision_dev.py
```

`init_dev.py` yangi lokal `.env`ga random Django secret va database parolini yozadi (0600), mavjud `.env`ni saqlaydi. `.env.example` variable nomlari konfiguratsiyaga mos. Compose ichida `POSTGRES_HOST=db`, `POSTGRES_PORT=5432` ishlatiladi.

Ushbu kompyuterdagi Compose 2.40.3 `build_bake.go` ichki panic bergani sabab build uchun `COMPOSE_BAKE=false` ishlatildi. Bu faqat buyruq uchun workaround; tizim sozlamalari o‘zgartirilmagan.

- Sayt: http://127.0.0.1:8080/
- Django Admin: http://127.0.0.1:8080/admin/
- Swagger: http://127.0.0.1:8080/api/docs/
- OpenAPI: http://127.0.0.1:8080/api/schema/
- Readiness: http://127.0.0.1:8080/health/

`provision_dev.py` dastlabki `localadmin` superuserni yaratadi. Username va random parol ignore qilingan **`.secrets/dev-admin.json`** ichida (0600); qiymatlar terminalga chiqarilmaydi. Mavjud akkaunt paroli avtomatik almashtirilmaydi. O‘zingiz tanlagan admin uchun:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py createsuperuser
```

`seed_demo` faqat `DEBUG=True`da 3 kategoriya va 6 mahsulotni, jumladan mavjud bo‘lmagan mahsulotni yaratadi. Barcha demo yozuv va rasmlar **namuna** deb belgilangan; qayta chaqirish mavjud yozuvlarni yangilamaydi. Haqiqiy mahsulot rasmlari, narx va tasdiqlangan yo‘riqnomalar Django Admin orqali kiritiladi.

## Foydalanuvchi oqimi

Kategoriyalar → kategoriya mahsulotlari → mahsulot detaili. Detailda nom, rasm, narx, mavjudlik, tavsif va oddiy matnli batafsil axborot bor. Guest “Saqlash”ni bosganda registratsiya ochiladi; mavjud akkaunt bilan login yo‘li ham bor. Ikkala holatda avval tanlangan mahsulot alohida Favorites API bilan avtomatik saqlanadi. “Saqlanganlar”da user o‘z ro‘yxatini ko‘radi va mahsulotni o‘chiradi.

Access JWT faqat JavaScript xotirasida. Refresh JWT HttpOnly, SameSite=Strict cookie’da. Auth POSTlar explicit CSRF/Origin tekshiruviga ega. Sahifa almashgach Save va Favorites oldidan silent refresh ishlaydi; bir tabdagi refreshlar bitta Promise orqali boshqariladi. sessionStorage faqat vaqtinchalik mahsulot intentini saqlaydi; Bekor/Back uni tozalaydi; auth sahifasining reloadi uni saqlaydi.

## API v1.1

| Method | Endpoint | Vazifa |
|---|---|---|
| GET | `/api/v1/categories/` | Public kategoriyalar |
| GET | `/api/v1/categories/{slug}/products/` | `{category, products}` |
| GET | `/api/v1/products/{slug}/` | Public detail |
| GET | `/api/v1/auth/csrf/` | CSRF token+cookie |
| POST | `/api/v1/auth/register/` | Registration + access/cookie |
| POST | `/api/v1/auth/token/` | Login + access/cookie |
| POST | `/api/v1/auth/token/refresh/` | Cookie orqali rotation |
| POST | `/api/v1/auth/logout/` | Blacklist va cookie tozalash |
| GET, POST | `/api/v1/me/saved-products/` | JWT user list/save |
| DELETE | `/api/v1/me/saved-products/{product_id}/` | O‘z relationini o‘chirish |

Yangi Save 201, duplicate 200, invalid/not found `product_id` 400, boshqa user/mavjud bo‘lmagan relationni DELETE 404. Product ma’lumotlari favoritesga nusxalanmaydi. Katalog CRUD faqat Django Admin orqali.

## Tekshirish

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py migrate --noinput
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py test
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py spectacular --validate --fail-on-warn --file /tmp/herbal-openapi.yaml
python3 scripts/browser_smoke.py
```

Browser smoke uchun lokal Chrome kerak (`--chrome /path/to/chrome`). Skript yangi vaqtinchalik browser profili va demo userdan foydalanadi, credential/tokenlarni chiqarmaydi. Screenshotlar `/tmp/herbal-store-browser/`ga yoziladi. Regression harness `/tests/index.html`da 41 ta auth/navigation/UI/UZ-RU mock API tekshiruvini haqiqiy browserda bajaradi.

## UI/UX refinement — 2026-11-01

Nom va logo uchun yagona frontend konfiguratsiyasi: `frontend/js/config.js` ichidagi `siteConfig.name` va `siteConfig.logoUrl`. Hozirgi `Herbal Store` vaqtinchalik nom; haqiqiy logoni frontend assetiga joylab, masalan `/assets/logo.png` yo‘lini kiriting. Logo bo‘sh, yaroqsiz yoki yuklanmagan bo‘lsa mavjud barg belgisi qoladi. Nom header, hero, login/register, footer, sahifa title va meta descriptionga qo‘llanadi. Django Admin sarlavhalari standart Django sozlamalari orqali `backend/config/urls.py`da boshqariladi.

Kategoriya va detail ochilganda silent refresh hamda Favorites GET orqali haqiqiy holat o‘qiladi. Konturli bookmark + **Saqlash** POST bilan qo‘shadi; yashil bookmark + **Saqlangan** DELETE bilan olib tashlaydi. Xatoda oxirgi tasdiqlangan holat qoladi; dastlabki holat aniqlanmasa **Qayta tekshirish** faqat GETni takrorlaydi. Favorites sahifasidagi **O‘chirish** saqlangan. Browser Back orqali xotiradan qaytilganda eski access token tashlanadi va joriy cookie sessiyasi bilan ma’lumot qayta yuklanadi.

Kategoriya/Saqlanganlar kartalari barcha ekranlarda vertikal: rasm, nom, mavjudlik, narx va ustma-ust **Batafsil** hamda Save/Remove tugmalari. Grid: mobil 2; 700px dan 3; 1000px dan 4; 1400px dan 5 ustun. Rasmlar qirqilmaydi; tugmalar 12px radius va kamida 44px balandlikda. Saqlangan sana Toshkent vaqti bilan `Saqlangan: 14.10.2026` shaklida. Qisqa tavsif va batafsil yo‘riqnoma detail sahifasida qoladi.

**Chiqish** avval **Hisobdan chiqish** tasdiqlash oynasini ochadi. **Bekor qilish** yoki Escape sessiyani saqlaydi; **Ha, chiqish** mavjud logoutni bajaradi. Fokus oynaga o‘tadi va bekor qilinganda tugmaga qaytadi. Login/register parol ko‘zchasi va mavjud Django Admin ishlashi saqlangan.

Admin assetlari yangilangach:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py collectstatic --noinput
```

Yakuniy tekshiruv: Django **80/80 PASS**, frontend **34/34 PASS**; Chrome’da 280/320/390/768/1024/1440/1600px kengliklarda katalog/Saqlanganlar uchun **14 responsive ssenariy PASS**. Haqiqiy Save/auth/pending Save, logout tasdiqlash, klaviatura/fokus hamda mavjud Admin smoke tekshiruvlari o‘tdi. Mobil tekshiruv Chrome emulyatsiyasida bajarilgan; jismoniy telefon tekshirilmagan.

UI regressionlarini real bazaga yozmasdan tekshirish:

```bash
python3 scripts/browser_smoke.py --regression-only
```

To‘liq Chrome smoke mavjud tartibda yangi sinov foydalanuvchisi yaratadi; mavjud katalogni o‘zgartirmaydi. So‘nggi natijalar va o‘zgargan fayllar: [yakuniy karta/logout hisoboti](docs/implementation/FINAL-PRODUCT-CARDS-REPORT.md). Avvalgi o‘zgarishlar: [UI/UX hisoboti](docs/implementation/UI-UX-REFINEMENT-REPORT.md).

## Lokal infratuzilma

Loyiha nomi `herbal_store_mvp_dev`; PostgreSQL/media/static uchun shu nomdagi persistent volumelar va alohida tarmoqlar bor. Hostga Nginx `127.0.0.1:8080` va `.env`dagi aniq `WEB_LAN_IP:8080` orqali publish qilinadi; backend/DB portlari yopiq. Backend non-root Gunicorn bilan ishlaydi. Startup migration va collectstatic bajaradi; Nginx frontend, media/static, API/Admin routingni beradi.

Wi-Fi DHCP manzili o‘zgarsa `ip -brief -4 address show` bilan joriy IPni aniqlang.
`.env`dagi `WEB_LAN_IP`, `DJANGO_ALLOWED_HOSTS` va
`DJANGO_CSRF_TRUSTED_ORIGINS`ning LAN yozuvini birga moslang. So‘ng mavjud
image/volumelarni saqlagan holda yangi sozlamalarni yuklang:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --no-build --force-recreate --wait backend web
```

Bu backend startup migratsiyasini ham bajaradi; yangi pending migration bo‘lsa
avval backup va ruxsat tartibiga amal qiling. `0.0.0.0`ga kengaytirish talab qilinmaydi.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=100 backend web
docker compose -f docker-compose.yml -f docker-compose.dev.yml stop
```

`stop` ma’lumotlar volumelarini saqlaydi. Frontend/backend source dev bind-mountda; JS/CSS uchun reload, Python uchun Gunicorn `--reload` bor. Yangi migration qo‘shilsa `migrate` ishlating. Requirements yoki Dockerfile o‘zgarsa image’ni qayta build qiling.

Lokal HTTP sabab `DEBUG=True`; production/AWS/HTTPS deployment bu vazifada bajarilmagan. Swagger/schema DEBUG muhitidagina ochiladi. Productionga o‘tishdan oldin haqiqiy katalog kontenti, HTTPS, deployment settings va backup/restore sinovi alohida bajariladi. Cart/order/delivery/payment/search MVP tarkibiga kirmaydi.
