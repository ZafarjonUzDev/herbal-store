# Herbal Store — lokal MVP implementatsiya va runtime hisoboti

**Sana:** 2026-10-13 (Asia/Samarkand).  
**Holat:** lokal MVP implementatsiya qilindi va real PostgreSQL/Chrome bilan tekshirildi.  
**URL:** http://127.0.0.1:8080/

## Ishlaydigan funksiyalar

1. Django Admin session login va Category/Product CRUD, image upload, validatorlar, filterlar.
2. Anonim kategoriyalar ro‘yxati; kategoriya mahsulotlari `{category, products}` kontraktida.
3. Product detail: nom, rasm, Decimal narx, mavjudlik, tavsif, oddiy matnli batafsil ma’lumot; site Back o‘z kategoriyasiga.
4. Username/password registratsiya va JWT login; case-sensitive username, Unicode NFKC va whitespace normalizatsiyasi.
5. HttpOnly refresh cookie, CSRF/Origin enforcement, silent refresh, rotation, blacklist/logout; access faqat JS memory.
6. Userga tegishli favorites save/list/delete; unique user/product, 201/200 idempotency, invalid ID400, other/missing relation404.
7. Guest Save → registratsiya yoki login → tanlangan mahsulot alohida Save API orqali avtomatik saqlanadi.
8. Auth reload pending Save’ni saqlaydi; validationda intent qoladi; Bekor/Back/boshqa sahifa havolasida tozalanadi.
9. Oltita responsive HTML/CSS/Vanilla JS sahifa: katalog, category, detail, favorites, login, register. Loading/empty/error/retry holatlari, keyboard/label/alt semantikasi.
10. OpenAPI/Swagger, backend/database/Nginx readiness va lokal Compose startup.

Cart, order, delivery, payment, search yoki boshqa biznes modul qo‘shilmadi. Katalog CRUD Django Admin orqali ishlaydi.

## Avvalgi kod va runtime gate

AGENTS, README, architecture v1.1, ADR-007..009 va Phase 1–3/runtime hisobotlari o‘rganildi. Mavjud User, Category/Product models/migrations, Admin, katalog API va auth lifecycle saqlandi. Accountsga minimal Unicode login normalizatsiyasi hamda OpenAPI annotatsiyalari qo‘shildi.

Qolgan modullardan oldin ajratilgan Compose PostgreSQLda `check`, `makemigrations --check --dry-run`, `migrate` va accounts+catalog testlari bajarildi: **55/55 PASS**, 10.510s. Oldingi vaqtinchalik cluster skripti ishlatilmadi. So‘ng favorites migration, frontend va lokal infratuzilma yakunlandi.

## Test natijalari

| Tekshiruv | Yakuniy natija |
|---|---|
| Django `check` | PASS — 0 issue |
| Migration drift | PASS — No changes detected |
| PostgreSQL `migrate` | PASS, favorites.0001_initial ham qo‘llandi |
| To‘liq Django suite | **77/77 PASS**, 12.201s |
| OpenAPI `spectacular --validate --fail-on-warn` | PASS — warnings/errors yo‘q |
| Dependency `pip check` | PASS — No broken requirements found |
| Chrome frontend regression harness | **16/16 PASS** |
| Haqiqiy Chrome user flow smoke | **PASS**, exit0 |
| Desktop va 390px mobile ko‘rik | PASS; horizontal overflow yo‘q |
| Yakuniy Docker image build/startup | PASS — 3/3 container healthy |
| Nginx `nginx -t` | PASS |
| Startupdan keyingi HTTP/static/media/schema | PASS — barcha tekshirilgan URL200,11 API method kontrakti |
| Lokal secret source scan | PASS —111 text file,0 leak; `.env`/Admin credential0600 |
| Python compileall | PASS |
| Editorconfig whitespace | PASS — 58 nonempty source file, 0 issue |

Django suite tarkibi: 6 foundation + 26 accounts auth + 24 catalog + 2 demo command + 19 favorites. Favorites testlarida haqiqiy PostgreSQL UNIQUE poygasi ikki parallel insert bilan majburan yaratiladi; natija bitta201, bitta200 va bitta relation. Ownership, JWT rad etish, malformed ID, CASCADE, unavailable save, joriy Product qiymatlari va N+1 query chegarasi ham tekshirildi. Django test database faqat loyiha PostgreSQL containerida yaratilib, suite oxirida tozalandi.

Chrome smoke real frontend/API bilan katalog → category → detail, product image, parent Back, guest registrationdan keyingi Save, login orqali duplicate Save, HttpOnly/storage chegaralari, favorites delete/empty, navigatsiyadan keyingi silent refresh, logout, auth reload, formvalidation, Bekor/browser Back, protected guest Favorites, network failure/retry va haqiqiy Django Admin login/product listni tekshirdi. Mock frontend harness CSRF headers, single-flight, bounded401 retry, 403/network handling, redirect/intent validation, token storage, logout/rotation tartibi va auth navigationni qamraydi.

Screenshotlar: `/tmp/herbal-store-browser/home-desktop.png`, `desktop.png`, `mobile.png`, `product-mobile.png`. Browser faqat yangi vaqtinchalik profil va random demo userdan foydalandi; credential/tokenlar chiqarilmadi. Test uchun yaratilgan `browser_*` demo userlar lokal bazada qolgan.

Ruff/Black/Flake8 mavjud emas; bu formatter/linterlar bilan tekshirildi deb da’vo qilinmaydi. Python syntax, haqiqiy ES module bajarilishi va mavjud editorconfig whitespace talablari tekshirildi.

## Infratuzilma va maxfiy konfiguratsiya

Loyiha `herbal_store_mvp_dev`; database, media/static volumelari va app/db tarmoqlari loyiha nomi bilan izolyatsiyalangan. PostgreSQL va Gunicorn hostga publish qilinmaydi; Nginx faqat `127.0.0.1:8080`. Backend non-root userda. Nginx frontend/static/media’ni beradi va API/Admin/health’ni Django’ga proxy qiladi; Host porti CSRF same-origin uchun saqlanadi. Docker logs10MiB×3 bilan cheklangan. `.env`, `.secrets` image context va Git ignore’dan chiqarilgan.

Pinlar: Python3.13.15-slim-bookworm va Nginx1.28-alpine digest bilan; PostgreSQL16.15-alpine digest bilan. Django5.2.18, DRF3.16.1, SimpleJWT5.5.1, psycopg3.3.6, python-dotenv1.2.2, Pillow11.3.0 pinlari saqlandi. Gunicorn26.2.0 WSGI uchun, drf-spectacular0.30.0 tasdiqlangan API hujjatlari uchun qo‘shildi; [Gunicorn rasmiy release](https://pypi.org/project/gunicorn/26.2.0/), [drf-spectacular rasmiy release](https://pypi.org/project/drf-spectacular/0.30.0/).

Compose2.40.3 `build_bake.go` ichki panic berdi; `COMPOSE_BAKE=false` bilan build muvaffaqiyatli bajarildi. [Rasmiy Compose issue](https://github.com/docker/compose/issues/13124) shu komponent muammosini qayd etadi. Tizim sozlamalari almashtirilmadi.

Lokal `.env`dagi avval yaratilgan random secretlar saqlandi, non-secret Compose parametrlar moslashtirildi. `init_dev.py` fresh checkout uchun `.env`ni yaratadi; `provision_dev.py` lokal superuserni tayyorlaydi. Admin credential `.secrets/dev-admin.json` (0600), `.env` ham0600. Username `localadmin`; parol hisobotga kiritilmadi. README startup/test/admin buyruqlarini beradi.

## Fayllardagi asosiy o‘zgarishlar

- `backend/apps/favorites/`: model,0001 migration, serializers, views, urls,19 test.
- `backend/apps/accounts/`: minimal LoginSerializer normalizatsiyasi, regression testi, schema annotatsiyalari.
- `backend/apps/catalog/`: category-envelope schema, `seed_demo` management command va2 test.
- `backend/config/`: favorites/schema/docs/health URLlar, OpenAPI app/settings, trusted proxy header; DB PostgreSQL bo‘lib qolgan.
- `backend/requirements.txt`: ikki kerakli pinned runtime paket.
- `frontend/`: oltita sahifa, CSS,4 ES modul, browser regression harness.
- Compose, backend/Nginx Dockerfile, entrypoint va Nginx konfiguratsiyalari, `.dockerignore`.
- `scripts/`: `.env` init, lokal Admin provision va dependency’siz Chrome CDP smoke.
- README, AGENTS, auth/frontend architecture, ADR-008, tarixiy runtime/Phase3 hisobotlari va ushbu hisobot.

Ish papkasida `.git` metadata yo‘q; Git commit/diff amallari bajarilmadi. Ignore qoidalari source/config review orqali tekshirildi.

## Qolgan ish

Lokal MVP funksiyalari yakunlandi. Hozir 3 kategoriya/6 mahsulot original DEMO/NAMUNA rasmlari va namunaviy narx/axborot bilan turibdi; haqiqiy do‘kon ma’lumotlari va tasdiqlangan yo‘riqnomalar Admin’da kiritilishi kerak.

AWS deployment, domen, HTTPS/sertifikat, production settings audit va production backup/restore sinovi ushbu lokal vazifada bajarilmadi. Bu natija production release tasdiqi emas; lokal HTTP muhit `DEBUG=True` bilan ishlaydi. Swagger/schema ham DEBUG muhitidagina ochiladi.
