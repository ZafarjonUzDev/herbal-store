# Phase 1–3 — runtime tekshiruv hisoboti

**Sana:** 2026-10-13  
**Dastlabki holat:** QISMAN TEKSHIRILDI; PostgreSQL integration verification PENDING.
**Yangilangan holat:** PostgreSQL integration verification PASS — quyidagi yangi bo‘limni ko‘ring.  
**Phase 4:** boshlanmadi; o‘tish mezoni hali bajarilmadi.

## Muhit

- Ubuntu 26.04.1 LTS.
- Tizim Python'i 3.14.4; Python 3.13 topilmadi. Loyiha `.venv` muhiti mavjud Python 3.12.2 bilan yaratildi. [Django 5.2 Python mosligi](https://docs.djangoproject.com/en/5.2/faq/install/) Python 3.12ni qamraydi; Python 3.13dagi tekshiruv bajarilmadi.
- `.venv`ga mavjud `backend/requirements.txt` o‘rnatildi: Django 5.2.18, DRF 3.16.1, SimpleJWT 5.5.1, psycopg/binary 3.3.6, python-dotenv 1.2.2, Pillow 11.3.0. Dependency pinlari o‘zgartirilmadi, yangi paket qo‘shilmadi.
- PostgreSQL 18.6 client/server binarylari mavjud. Tizimdagi `18/main` cluster `down`; u ishga tushirilmadi va ma’lumotlariga murojaat qilinmadi.
- Docker 29.1.3 va Compose 2.40.3 CLI mavjud; container yaratilmagan, daemon tekshirilmagan.
- `.env.example` asosida lokal `.env` yaratildi (`0600`), random Django secret va DB password qo‘yildi. Secretlar hisobot/logga chiqarilmadi. Konfiguratsiya `herbal_store_phase3_dev` nomli yangi baza uchun `127.0.0.1:55432`ga yo‘naltirilgan; baza/server **hali yaratilmagan**.
- Yangi PostgreSQL clusteri, development bazasi va Django vaqtinchalik test bazasini yaratish/o‘chirish uchun ruxsat so‘rovi **rad etildi**. Bu amallar bajarilmadi; sudo yoki tizim paketlarini o‘rnatish ishlatilmadi.
- Ish papkasida `.git` mavjud emas. Diff uchun boshlang‘ich manba nusxasi olindi. `.env`, `.venv/`, `.secrets/` ignore qoidalari loyiha tashqarisidagi vaqtinchalik Git metadata bilan tekshirildi; loyiha ichida Git repo yaratilmagan.

## Bajarilgan buyruqlar va natijalar

Python muhiti va dependency buyruqlari loyiha rootida bajarildi:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r backend/requirements.txt
.venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir -r backend/requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q backend
```

Birinchi pip urinishida sandbox DNS ishlamadi. Tarmoq ruxsati bilan qayta o‘rnatish muvaffaqiyatli; `pip check` — dependency ziddiyatlari yo‘q. `compileall` — PASS. Ruff/Black/Flake8 mavjud emas, shuning uchun bu vositalar bilan lint/format tekshiruvi bajarilmadi. O‘zgargan fayllar mavjud `.editorconfig` qoidalari bo‘yicha tekshirildi.

Quyidagi buyruqlar `backend/` ichida bajarildi:

```bash
../.venv/bin/python manage.py check
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py test apps.accounts.tests.test_configuration --verbosity 2
```

| Tekshiruv | Natija |
|---|---|
| `check`, tuzatishdan oldin va keyin | PASS: 0 issue |
| `makemigrations --check --dry-run` | `No changes detected`; model/migration drift yo‘q, lekin DB migration history tasdiqlanmadi |
| PostgreSQL ulanishi | Sandboxdan tashqaridagi qayta tekshiruvda ham `127.0.0.1:55432` connection refused; server mavjud emas |
| Foundation configuration tests | **4/4 PASS**, DB setup o'tkazib yuborildi |
| `manage.py migrate` | NOT RUN: alohida PostgreSQL bazasi tayyor emas |
| `manage.py test` / to‘liq accounts+catalog suite | NOT RUN: test bazasini yaratish/o‘chirishga ruxsat yo‘q |
| Admin CRUD, DB constraints, catalog API, haqiqiy JWT rotation/blacklist/logout integration | Runtime PENDING; source review bajarildi |
| Haqiqiy browser/production cookie sinovi | NOT RUN |

Suite inventarizatsiyasida **55 ta test** topildi: 6 foundation, 25 auth, 24 catalog. Shundan faqat yuqoridagi **4 ta konfiguratsiya testi** bajarildi; qolgan **51 ta test** o‘tgan deb hisoblanmaydi. Dastlab suite 48 ta edi; 7 ta auth regression testi qo‘shildi.

## Topilgan muammolar va minimal tuzatishlar

1. **401 o‘rniga 403.** Auth view autentifikatorlari bo‘sh bo‘lgani uchun DRF `AuthenticationFailed`ni challenge mavjud bo‘lmaganda `403`ga aylantirgan. `CookieAuthView.get_authenticate_header()` qo‘shildi: noto‘g‘ri credential va refresh cookie yo‘qligi kontrakt bo‘yicha `401`; public auth endpointlari Bearer authentication talab qilmaydi.
2. **O‘chirilgan user refreshida 500.** O‘rnatilgan SimpleJWT serializeri userni `.objects.get()` bilan oladi. `User.DoesNotExist` ushlanmagani uchun refreshda server xatosi chiqardi. Endi umumiy `401` va refresh cookie tozalash bilan boshqariladi.
3. **Unicode duplicate username 500 yo‘li.** DRF uniqueness validatsiyasi raw username'ni, Django `create_user()` esa NFKC normalizatsiya qilingan qiymatni ishlatgan. `Flower` va `Ｆｌｏｗｅｒ` shu sabab DB uniqueness konfliktiga olib kelishi mumkin edi. Normalizatsiya field validatorlaridan oldinga ko‘chirildi; `Ali` va `ali` case-sensitive qoladi.
4. **Lokal cookie testidagi DEBUG taxmini.** Django test runner odatda `DEBUG=False` qo‘yadi, mavjud test esa `Secure=False` talab qilgan. Auth test class uchun explicit `DEBUG=True`, mavjud production test uchun `DEBUG=False` saqlandi. Ushbu test tuzatishi PostgreSQL bilan hali bajarilmadi.

DB talab qilmaydigan vaqtinchalik runtime reproduksiyasida birinchi ikki xato tuzatishdan oldin namoyon bo‘ldi va keyin `401` bilan qayta tekshirildi. Refresh user lookup va login credential tekshiruvi bu reproduksiyada **mock qilindi**; bu haqiqiy DB integration testi emas. Username normalizatsiyasi uniqueness validatoriga canonical qiymat kelishi bilan tekshirildi; validatorning DB tekshiruvi mock qilindi.

Qo‘shimcha ravishda haqiqiy `APIClient(enforce_csrf_checks=True)` bilan barcha to‘rtta auth POSTda missing CSRF, invalid CSRF va untrusted Origin — **12 ta DBsiz tekshiruv** — `403` JSON qaytarishi tasdiqlandi. Bular yuqoridagi 4 ta Django test hisobiga qo‘shilmagan.

Qo‘shilgan 7 regression testi: Unicode duplicate, deleted-user refresh, inactive-user login, invalid/expired refresh, invalid/expired idempotent logout, barcha auth POSTlarda invalid CSRF va untrusted Originning session/token state'ga ta’sir qilmasligi. Ular PostgreSQL bilan bajarilishi kerak.

## O‘zgargan fayllar

- `backend/apps/accounts/serializers.py`
- `backend/apps/accounts/views.py`
- `backend/apps/accounts/tests/test_auth_api.py`
- `docs/architecture/05-auth-security.md`
- `docs/decisions/ADR-008-csrf-and-token-lifecycle.md`
- `README.md`
- Ushbu `docs/implementation/PHASE-1-3-RUNTIME-REPORT.md`

Faqat lokal artefaktlar: `.env`, `.venv/`; vaqtinchalik source snapshot, reproduksiya va PostgreSQL tayyorlash skriptlari loyiha tashqarisida `/tmp/`da. PostgreSQL tayyorlash skripti bajarilmadi. Modellar, migrations, katalog kodi, dependency pinlari va `deploy/nginx/.gitkeep` o‘zgartirilmadi.

## Tugatish uchun qolgan ish

Oldindan mavjud, bo‘sh va faqat ushbu loyihaga ajratilgan development/test bazalari yoki yangi izolyatsiyalangan bazani yaratish uchun ruxsat kerak. Shundan keyin `.env`ga mos ulanish sozlanadi va `backend/`da quyidagilar bajariladi:

```bash
../.venv/bin/python manage.py check
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py test
```

Oddiy Django test runner vaqtinchalik test bazasini yaratadi va oxirida o‘chiradi; bu faqat ajratilgan test bazasi uchun oldindan ruxsat bilan qilinadi. PostgreSQL migrationlari va barcha testlar muvaffaqiyatli tugamaguncha Phase 1–3 runtime verification yakunlandi yoki Phase 4ga tayyormiz, deb hisoblanmaydi.


## Keyingi lokal MVP tekshiruvi — 2026-10-13

Foydalanuvchi butun lokal MVPni yakunlashni va faqat Herbal Store uchun Docker Compose database yaratishni so‘radi. Oldingi vaqtinchalik PostgreSQL cluster skripti ishlatilmadi. `herbal_store_mvp_dev` loyihasi uchun izolyatsiyalangan PostgreSQL 16.15, Python 3.13.15/Django 5.2.18, Gunicorn va Nginx ishga tushirildi.

Phase 4 kodini yozishdan **oldin** Compose ichida:

- `manage.py check` — 0 issue.
- `makemigrations --check --dry-run` — No changes detected.
- `migrate --noinput` — migrations muvaffaqiyatli qo‘llandi; qayta chaqirishda pending migration yo‘q.
- `test apps.accounts apps.catalog` — **55/55 PASS**, 10.510 soniya; haqiqiy PostgreSQL test database yaratildi va suite oxirida tozalandi.
- `pip check` — No broken requirements found.

Shu natija Phase 1–3 runtime gate’ni yopdi. Keyin Favorites/frontend qo‘shildi; yakuniy to‘liq suite **76/76 PASS**, 11.356 soniya. Avvalgi hisobot bo‘limlari o‘sha tekshiruvdagi tarixiy holatni saqlaydi. Joriy ishga tushirish va browser natijalari [MVP lokal hisobotida](MVP-LOCAL-REPORT.md).

Yakuniy ko‘rikdagi Unicode login normalizatsiyasi regressiyasi qo‘shilgach to‘liq suite yana bajarildi: **77/77 PASS**, 12.201 soniya. Frontend yakuniy regressionlari **16/16 PASS** va to‘liq Chrome smoke **PASS**.
