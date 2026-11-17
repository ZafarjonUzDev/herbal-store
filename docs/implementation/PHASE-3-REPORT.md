# Phase 3 — Customer Authentication & JWT (source complete, runtime NOT verified)

**Sana:** 2026-10-12  
**Arxitektura:** v1.1  
**Holat:** Fazaning source kodi va Django testlari yozilgan, ammo Django/PostgreSQL runtime testi bajarilmagan.

## Amalga oshirilgan

- `apps/accounts/serializers.py`: username + password; Django password validators; `create_user` password hashing; public registration staff/superuser huquqini olmaydi.
- `apps/accounts/views.py`: GET CSRF token; POST register, login, refresh, logout.
- `apps/accounts/urls.py`: `/api/v1/auth/` marshrutlari.
- `config/urls.py`: accounts URL larini mavjud catalog API yoniga qo‘shish.
- `config/settings.py`: CSRF JSON error view, secure-cookie sozlamalari, auth ScopedRateThrottle limitlari.
- `apps/accounts/tests/test_auth_api.py`: **18 ta test metodi** — CSRF, origin, cookie, JWT, duplicate username, inactive user, refresh rotation, revoked old token, logout va production cookie testlari.

## JSON contract va cookies

| Metod | Endpoint | Status | Response / cookie |
|---|---|---|---|
| GET | `/api/v1/auth/csrf/` | 200 | `{"csrfToken": "..."}` + Django CSRF cookie |
| POST | `/api/v1/auth/register/` | 201 | `{"user": {"id": ..., "username": "..."}, "access": "..."}` + refresh HttpOnly cookie |
| POST | `/api/v1/auth/token/` | 200 | `{"access": "..."}` + refresh HttpOnly cookie |
| POST | `/api/v1/auth/token/refresh/` | 200 | `{"access": "..."}` + yangi refresh HttpOnly cookie |
| POST | `/api/v1/auth/logout/` | 204 | Bo‘sh response; refresh blacklist, cookie delete |

**Security:** barcha POST endpointlari `X-CSRFToken`ni talab qiladi; Django/DRF APIView `dispatch` ichida `csrf_protect` aniq ishlatiladi. Auth CSRF xatosi API uchun JSON `403`. Origin tekshiruvi Django CSRF himoyasining tarkibiy qismi. Cookie haqiqiy productionda `__Secure-refresh; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/`. `DEBUG=True` localhostda cookie `refresh_token` va `Secure=False` bo‘ladi. Refresh token JSONga chiqmaydi.

Simple JWT `TokenRefreshSerializer`dan foydalaniladi, chunki u token validity, active user, rotation va blacklistni tekshiradi. Oldingi refresh token blacklist qilinadi. Access JWT stateless: logout vaqtida avval berilgan access JWT muddati tugamaguncha yaroqli qolishi mumkin, browser esa uni JS memorydan o‘chirishi kerak (frontend Phase 5).

Rate-limits: register `5/hour`, login `10/min`, refresh/logout `30/min` (DRF ScopedRateThrottle, odatda IP va Django cache asosida; multiworker production anti-brute-force kafolati emas). `flushexpiredtokens` commandini productionda davriy ishga tushirish keyingi deployment vazifasi.

## Testlar va muhit

**Bajarilgan**:

- Python AST/compile tekshiruvi (`python -m compileall -q backend`) — syntax to‘g‘ri.
- API endpoint/kod inventarizatsiyasi va ZIP integrity tekshiruvi.
- Phase 1–2 arxitektura/ADR hujjatlari saqlandi.

**Bajarilmagan**:

- `manage.py check`, migration checks, DB migrations.
- Django `manage.py test` (Phase 1–3 avtomatik testlari).
- Browser cookie/CSRF testlari, production deployment, Docker/AWS.

Sababi: ushbu fayl yig‘ilgan container muhitida Django/DRF/SimpleJWT paketlari yo‘q, pip index tarmog‘i mavjud emas va PostgreSQL service yo‘q. `pip install` bilan tekshiruv muvaffaqiyatsiz tugadi. Paketlar ishga tushgach quyidagi buyruqlar majburiy:

```bash
# loyiha rootida: .env dagi real secret/DB settingsni kiriting
python -m pip install -r backend/requirements.txt
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test apps.accounts apps.catalog
```

**Qabul mezoni:** yuqoridagi buyruqlarning barchasi real PostgreSQL va o‘rnatilgan Django bilan muvaffaqiyatli tugamaguncha Phase 1–3 runtime tekshirildi, deb hisoblanmaydi.

## Chegara

- Favorites modeli yoki Favorites API hali mavjud emas — Phase 4.
- Frontend `auth.js`, silent refresh va pending Save orkestrlash hali mavjud emas — Phase 5.
- Docker/Nginx/AWS va real browser testi hali bajarilmagan — Phase 6–8.
- `User`ga email/phone, password recovery, SMS, order, cart, delivery qo‘shilmadi.

## Keyingi qadam

1. Codex/terminal yordamida Phase 1–3 runtime verify va kamchiliklar bo‘lsa minimal tuzatish.
2. So‘ng Phase 4 Favorites modeli + user-owned save/list/delete API.


## Runtime gate yakunlandi — 2026-10-13

Izolyatsiyalangan Herbal Store Compose PostgreSQL 16.15/Python 3.13.15 muhitida `check`, `migrate`, migration drift tekshiruvi va mavjud accounts+catalog **55 ta test** muvaffaqiyatli o‘tdi. CSRF/Origin rad etish, cookie sozlamalari, rotation/blacklist/logout va oldingi regression testlari haqiqiy DB bilan tekshirildi. Shu tekshiruvdan so‘ng foydalanuvchi so‘ragan qolgan lokal MVP implementatsiya qilindi. [Joriy hisobot](MVP-LOCAL-REPORT.md).
