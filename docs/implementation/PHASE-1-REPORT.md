# Phase 1 — Django Foundation bajarilgan ishlar

**Holat: SOURCE READY / RUNTIME NOT VERIFIED**  
**Sana:** 2026-10-12

## Ishlangan

- `backend/manage.py`, `config/settings.py`, `urls.py`, `wsgi.py`, `asgi.py` yozildi.
- `apps.accounts`, `apps.catalog`, `apps.favorites` Django AppConfig va skeletonlari ochildi.
- `accounts.User(AbstractUser)` va birinchi `accounts/migrations/0001_initial.py` yaratildi.
- Django Admin uchun custom `User` standard `UserAdmin` bilan ro‘yxatga olindi.
- PostgreSQL `POSTGRES_*` environment o‘zgaruvchilariga ulandi (konfiguratsiya darajasida).
- DRF default JWT authentication, fail-closed IsAuthenticated va Simple JWT blacklist/rotation konfiguratsiyasi qo‘shildi. Browser login/refresh/logout endpointlari **yozilmadi**.
- 6 ta minimal foundation test case yozildi (barcha testlar birgalikda hisoblangan).
- Frontend, Docker/Compose, Category, Product, Favorites, JWT endpointlari ataylab yozilmadi.

## Python dependencies

| Paket | Versiya | Sabab |
|---|---|---|
| Django | 5.2.18 | LTS, Python 3.13ga mos |
| djangorestframework | 3.16.1 | Django 5.2ga mosligi e’lon qilingan |
| djangorestframework-simplejwt | 5.5.1 | JWT va refresh blacklist |
| psycopg[binary] | 3.3.6 | PostgreSQL drayveri |
| python-dotenv | 1.2.2 | Lokal `.env`ni yuklash |

## Tekshiruv matritsasi

| Tekshiruv | Holat |
|---|---|
| Python syntax / AST | PASS — 28 ta `.py` fayl parse qilindi va compileall xatosiz o‘tdi |
| `django-admin` / `manage.py check` | BAJARILMADI: Django o‘rnatilmagan |
| `makemigrations --check --dry-run` | BAJARILMADI: Django o‘rnatilmagan |
| `migrate` / PostgreSQL | BAJARILMADI: PostgreSQL server yo‘q |
| `manage.py test` | BAJARILMADI: Django o‘rnatilmagan / PostgreSQL yo‘q |
| `.gitignore` (maxfiy .env, media, __pycache__) | PASS — git check-ignore bilan tekshirildi |
| Docs (architecture va ADR) | PASS — Phase 0 bilan SHA-256 bo‘yicha bir xil |
| Docker/Compose | Phase 6ga qoldirilgan |

Paket yuklash uchun kerakli tarmoq bu muhitda ishlamadi. Migration **Django tooling bilan generatsiya qilinmagan**; lokal Django muhitida `makemigrations --check --dry-run` va testlar bilan tekshirish shart.

## Phase 2ga kirish sharti

Django 5.2.18 o‘rnatilgan PostgreSQL muhitida `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate`, `python manage.py test apps.accounts` komandalarini xatosiz bajarish, shundan keyin Category/Product modellari va Django Admin katalog CRUDga o‘tish.
