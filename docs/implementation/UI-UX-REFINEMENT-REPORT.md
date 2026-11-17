# Herbal Store — UI/UX refinement hisoboti

Sana: **2026-11-01**, lokal muhit. API kontrakti, domain modellari, migrationlar, JWT cookie/CSRF siyosati, admin ruxsatlari va mavjud katalog ma’lumotlari saqlandi. Yangi package, biznes funksiya yoki API qo‘shilmadi.

## Tuzatishlar

- Kategoriya/detail ochilganda cookie orqali silent refresh va Favorites GET haqiqiy saqlangan holatni tiklaydi. Konturli bookmark + **Saqlash** POST qiladi; ichi yashil bookmark + **Saqlangan** DELETE qiladi. Galochka ishlatilmaydi.
- Mutatsiya xatosida oxirgi tasdiqlangan holat qoladi. Boshlang‘ich holatni aniqlash xatosida **Qayta tekshirish** GETni qaytaradi; taxminiy Save/Delete yuborilmaydi. DELETE 404 allaqachon yo‘q relation sifatida aks etadi.
- Reload, qayta login va browser Back holati tiklanadi. Bfcache’dan qaytganda eski document access tokeni tashlanib joriy cookie ishlatiladi. Remove paytidagi auth xatosi tasodifiy pending Save yaratmaydi.
- Guest Save → registration yoki login → alohida Favorites POST oqimi va Bekor/Back intent tozalashi saqlandi. Favorites’dagi **O‘chirish** ishlaydi.
- Kategoriya/Favorites kartalari umumiy rasm/ma’lumot tartibida: desktopda 50/50, tor ekranlarda moslashuvchan ustma-ust ko‘rinish. `object-fit: contain`; **Batafsil** va Save/Remove mustaqil. Semantik Back/Bekor havolalari vizual tugmaga aylantirildi; productning to‘g‘ri kategoriyasiga qaytishi saqlandi.
- `frontend/js/config.js` — frontend nom/logo yagona konfiguratsiyasi. Header, hero, login/register, footer, title va meta description foydalanadi. Hozir `Herbal Store`, logo berilmaganida mavjud barg SVG qoladi; logo yuklash xatosida ham fallback ishlaydi. Admin server brendingi `backend/config/urls.py`da native `admin.site` sozlamasi bilan.
- Login/register parol ko‘zchasi, keyboard/focus/aria holatlari va amaldagi to‘rtta Django password validatoriga mos sodda yordam matni qo‘shildi.
- Sana Toshkent vaqti bilan **Saqlangan: 14.10.2026** shaklida; footer takroriy matni olib tashlandi. Qisqa tavsif va do‘kon tasdiqlagan batafsil qadoq/yo‘riqnoma matni alohida saqlandi.
- Django Admin’da yashil tema, o‘zbekcha form label/help/sarlavhalar, readonly mavjud rasm preview’i va tanlangan lokal rasm preview’i. Staff/model permissionlari va CRUD xulqi saqlandi.

## O‘zgargan fayllar

| Fayllar | Maqsadi |
|---|---|
| `frontend/index.html`, `category.html`, `product.html`, `favorites.html`, `login.html`, `register.html` | Umumiy brend hooklari, Back/Bekor tugmalari, parol markup’i, footer |
| `frontend/js/config.js` (yangi) | Vaqtinchalik do‘kon nomi va logo manzili |
| `frontend/js/app.js` | Favorites toggle/holat, kartalar, sanalar, brend, parol, browser Back |
| `frontend/js/auth.js` | Bfcache’dan qaytganda eski memory accessni tashlash |
| `frontend/css/styles.css` | Izchil kartalar, contain rasmlar, bookmark, navigatsiya, responsive/parol stillari |
| `frontend/tests/regression.js`, `frontend/tests/fixture.js` (yangi), `frontend/tests/logo.svg` (yangi) | Mavjud auth testlari va haqiqiy sahifa kodiga mock API regressionlari |
| `scripts/browser_smoke.py` | Real Chrome UI/API regressionlari va `--regression-only` rejimi |
| `backend/apps/catalog/admin.py` | Native formalar, tarjimalar, readonly preview |
| `backend/apps/catalog/apps.py`, `backend/apps/accounts/apps.py` | Admin ilova sarlavhalari |
| `backend/apps/catalog/static/catalog/admin.css` (yangi), `admin-image-preview.js` (yangi) | Admin tema va lokal tanlangan rasm preview’i |
| `backend/templates/admin/base_site.html` (yangi), `backend/config/settings.py` | Standart Admin template’iga tema assetini ulash |
| `backend/config/urls.py` | Admin brending va asosiy sarlavhalar |
| `backend/apps/catalog/tests/test_admin.py` | 3 yangi preview/required instruction/permission regressioni |
| `README.md`, `docs/architecture/06-frontend.md` | Konfiguratsiya, foydalanish va UI holatlari |
| `docs/decisions/ADR-002-django-admin.md`, `ADR-008-csrf-and-token-lifecycle.md` | Native Admin refinement va favorites/bfcache lifecycle aniqlashtirishi |
| `docs/implementation/UI-UX-REFINEMENT-REPORT.md` (ushbu fayl) | Natijalar va tekshirish chegaralari |

## Bajarilgan tekshiruvlar

Barcha Django buyruqlari mavjud `herbal_store_mvp_dev` Compose loyihasidagi backend containerida bajarildi:

| Tekshiruv | Natija |
|---|---|
| `python manage.py check` | PASS — 0 issue |
| `python manage.py test` | **80/80 PASS**, PostgreSQL’dagi alohida test bazasi; 12.979 s |
| `python manage.py makemigrations --check --dry-run` | PASS — `No changes detected` |
| `python manage.py migrate --check` | PASS — kutilayotgan migration yo‘q; schema o‘zgartirilmadi |
| `python manage.py spectacular --validate --fail-on-warn --file /tmp/herbal-uiux-openapi.yaml` | PASS |
| `python manage.py collectstatic --noinput` | PASS — yangi admin assetlari Nginx static volume’iga chiqarildi |
| Python AST syntax, 6 HTML sahifada ID yagonaligi, o‘zgargan source whitespace | PASS |
| Chrome frontend auth/navigation/UI mock API regressionlari | **31/31 PASS** — auth/navigation, actual-page UI, bfcache/account switch, logo success/fallback |
| Real Chrome desktop/mobile smoke | PASS — guest registration/login pending Save, toggle, reload, logout/login, network failure/retry, Favorites Remove, sanalar, alohida Batafsil, parol ko‘zchasi |
| Real Chrome Admin | PASS — login, katalog ro‘yxati, mavjud rasm, yangi fayl tanlash va tanlovni bekor qilish preview’i; katalog formasi submit qilinmadi |

Product update/delete Django testlarida alohida test bazasida tekshirildi: admin create/update/delete, keyingi GET’da yangi narx, favorites’da joriy product ma’lumotlari va CASCADE. Frontend mock regressionlari yangilangan narx/tavsif/yo‘riqnoma, detail 404 va relation DELETE 404 holatlarini qoplaydi. Haqiqiy mavjud katalog mahsulotlari test uchun o‘zgartirilmadi/o‘chirilmadi.

Desktop **1440×1000** va mobil **390×844** ko‘rinishlari Chrome’da tekshirildi; category/detail/register hamda Admin screenshotlari vizual ko‘zdan kechirildi. Screenshotlar: `/tmp/herbal-store-uiux-browser/`. Browser smoke yangi vaqtinchalik Chrome profili va yangi sinov foydalanuvchisidan foydalanadi; credential/tokenlar log qilinmaydi. Mock regression rejimi real bazaga yozmaydi.

Qayta tekshirish:

```bash
python3 scripts/browser_smoke.py --regression-only
python3 scripts/browser_smoke.py --output /tmp/herbal-store-uiux-browser
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py test
```

## Tekshirish uchun URL’lar

- Bosh sahifa: http://127.0.0.1:8080/
- Namuna kategoriya: http://127.0.0.1:8080/category.html?slug=demo-choylar
- Namuna product: http://127.0.0.1:8080/product.html?slug=demo-limon-oti
- Saqlanganlar: http://127.0.0.1:8080/favorites.html
- Login: http://127.0.0.1:8080/login.html
- Registration: http://127.0.0.1:8080/register.html
- Django Admin: http://127.0.0.1:8080/admin/
- Product boshqaruvi: http://127.0.0.1:8080/admin/catalog/product/
- Frontend regressionlar: http://127.0.0.1:8080/tests/index.html
- Readiness: http://127.0.0.1:8080/health/

## Muhit va qolgan cheklovlar

- Ushbu workspace `.git` papkasi Git metadata’sini bermaydi: `git status` **not a git repository** bilan tugadi. Git diff/commit yaratilmagan. Boshlang‘ich source nusxasi `/tmp/herbal-uiux-before/`da; maxfiy `.env`/`.secrets` nusxaga kiritilmagan. O‘zgarishlar shu nusxa bilan taqqoslandi.
- Haqiqiy nom/logo do‘kon tomonidan hali berilmagan. `frontend/js/config.js`ni yangilash yetarli; `logoUrl` uchun same-origin asset yo‘li ishlatiladi.
- Browser tekshiruvi Chrome’da bajarildi; Safari/Firefox tekshirilmagan. Native Django Admin’ning ayrim framework/uchinchi tomon matnlari Django paketidagi mavjud tarjima holatida qoladi.
- Lokal `.venv`da `drf_spectacular` yo‘q; yakuniy backend natijalari barcha dependency mavjud amaldagi Docker muhitidan olindi.
- Yakuniy `docker compose ... ps`: avvalgi backend/db/web containerlari (2 hafta oldin yaratilgan) uchalasi ham **healthy**; faqat `127.0.0.1:8080` publish qilingan. PostgreSQL/media/static volumelari saqlandi. Compose down/prune/reset bajarilmadi; AWS yoki production deployment boshlanmadi.
