# Phase 2 — Catalog + Django Admin — hisobot

**Holat:** Phase 2 source code va testlar yozildi. **Runtime tasdiq: PENDING.**

## Nima tayyorlandi?

- `apps.catalog.models.Category`: unique name/slug, timestamp, tartib.
- `apps.catalog.models.Product`: PROTECT category, image, Decimal narx, CHECK constraint, mavjudlik, tavsif va majburiy batafsil ma'lumot.
- Django Admin orqali Category/Product CRUD; `prepopulated_fields`, qidiruv, filter, readonly timestamp.
- Ommaviy va faqat o‘qishga mo‘ljallangan DRF endpointlar:
  - `GET /api/v1/categories/` → JSON array.
  - `GET /api/v1/categories/{category_slug}/products/` → `{category, products}`.
  - `GET /api/v1/products/{product_slug}/` → detail, `category.slug` bilan.
- DRF serializerlar: list/detail alohida; narx JSON string, rasm absolute URL, mavjud emas mahsulotlar ham chiqadi.
- `Cache-Control: no-store` public katalog GET javoblari uchun.
- `catalog/migrations/0001_initial.py` — katalogning qo‘lda yozilgan dastlabki migratsiyasi.
- `catalog/tests/` — modellar, public API, admin integratsiyasi testlari.
- `Pillow==11.3.0` qo‘shildi (`ImageField` / Django Admin rasm tekshiruvi uchun).
- Phase 1 sozlamasidagi `STATIC_URL` va `MEDIA_URL` boshiga `/` qo‘shildi, aks holda API rasmlari to‘g‘ri absolute URLga aylanmasligi mumkin.

## Modellarning qoidalari

- Category → Product: `PROTECT`.
- Product narxi: `MinValueValidator(0)` + `CHECK (price >= 0)`.
- Product `image`: bitta rasm; `.jpg/.jpeg/.png/.webp` va 5 MiB limit (Django Admin rasm mazmunini Pillow bilan tekshiradi).
- Product `detailed_information`: majburiy oddiy matn; HTML bajarilmasin.
- Product `is_available=False`: Product DBda va public API'da qoladi.
- Category/Product slugi: unique va public URL uchun barqaror; admin ongli ravishda o‘zgartirishi mumkin.
- Public API'larda create/update/delete yo‘q; CRUD Django Admin'da.

## Tekshiruv holati

| Tekshiruv | Holat |
|---|---|
| Python sintaksis/compileall | PASS (shu muhitda) |
| Kontraktga mos fayl va marshrutlar statik ko‘rik | PASS (shu muhitda) |
| ZIP archive integrity | PASS (shu muhitda) |
| Django `manage.py check` | NOT RUN |
| Django `makemigrations --check --dry-run` | NOT RUN |
| PostgreSQL `manage.py migrate` | NOT RUN |
| Django test suite | NOT RUN |
| Django Admin orqali real brauzerda CRUD | NOT RUN |

**Nega NOT RUN?** Ishlatilgan muhitda Django/DRF/Psycopg/Pillow va PostgreSQL server mavjud emas. `pip install` ham DNS/repositoryga ulana olmadi. Shuning uchun **migration fayli Django'ning o‘zi bilan yaratilgan yoki tekshirilgan deb aytish mumkin emas**. Runtime tekshiruvida drift chiqsa, Django-generated migration bilan solishtirib tuzatish kerak.

## Ishga tushirganda majburiy tekshiruv

Avval `README.md` bo‘yicha PostgreSQL, venv va `.env`ni tayyorla. Keyin:

```bash
cd herbal_store/backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test apps.accounts apps.catalog
python manage.py createsuperuser
python manage.py runserver
```

`makemigrations --check --dry-run` boshqa migration kerakligini aytsa, migrationni avtomatik ravishda ko‘r-ko‘rona qabul qilmasdan oldin model/migration mosligini tekshir. `test_admin` rasm yuklash uchun vaqtinchalik katalogdan foydalanadi.

API smoke test:

```bash
curl -i http://127.0.0.1:8000/api/v1/categories/
```

Django Admin orqali kategoriya va rasmli mahsulot yaratgach, category products/detail API'larni tekshir. Media fayllarini ishlab chiqish muhitida ko‘rish uchun debug-only media serving keyingi frontend/Docker fazada Nginx bilan yakunlanadi; hozircha `/media/` URL production tayyor degani emas.

## Qolgan ishlar va xavflar

- **Asosiy blocker:** Phase 1/2 Django runtime + PostgreSQL migratsiyalari real test qilinmagan. Buni testdan o‘tgan deb belgilamang; keyingi release oldidan bartaraf qilinsin.
- `SavedProduct` modelini **Phase 4**dan oldin qo‘shmang; SavedProduct CASCADE integration testi o‘sha fazada yoziladi.
- JWT/register/favorites endpointlari hali yo‘q; **Phase 3–4** uchun qoldirilgan.
- Swagger va `/api/schema/` hozirgi fazada mavjud emas, API docs keyingi scope'da qo‘shiladi.
- Docker/Nginx frontend hozircha yo‘q; rasm haqiqiy internetga Nginx orqali keyin xizmat qilinadi.
- Real mahsulot yo‘riqnomasi va rasmlarini faqat do‘kon tasdiqlagan manbadan kiriting.
