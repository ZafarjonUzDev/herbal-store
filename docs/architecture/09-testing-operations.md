# 09 — Testing & Operations

## 1. Test qatlamlari

### Model/database tests
- Category/Product slug uniqueness.
- Product narxi manfiy bo‘lmasligi (validator va bevosita DB insert/UPDATE uchun CHECK constraint).
- Productga bog‘langan category `PROTECT` bilan o‘chmaydi.
- Product/User o‘chirilganda SavedProduct CASCADE qoidalari.
- `UniqueConstraint(user, product)` duplicate bookmarkni bloklaydi.

### API tests
- Guest category list, category products va product detailni oladi; category products response `category` va `products` kalitlarini qaytaradi.
- Missing slug 404.
- Guest protected Favorites endpointiga kira olmaydi.
- Registration password hash qiladi; noto‘g‘ri input rad etiladi.
- Login success/error response va cookie sozlamalari; `__Secure-` prefiksiga mos `Secure=True` productionda.
- Refresh cookie + CSRF header oqimi. CSRF yo‘q yoki noto‘g‘ri bo‘lsa, cookie o‘rnatuvchi barcha auth POSTlar 403 (CSRF tekshiruvi yoqilgan test client bilan).
- Logout cookie tozalaydi va refresh tokenni bekor qiladi.
- Authenticated user save/list/delete qila oladi.
- User A User Bning bookmarkini ko‘rmaydi/o‘chirmaydi.
- Duplicate save duplicate database row yaratmaydi va 200 qaytaradi; parallel race 500 bermaydi.
- Public user Product/Category CRUD qila olmaydi.

### Frontend/browser tests
- Category → products → detail navigation.
- Site Back va browser Back xatti-harakati: root self-loop yo‘q; category→root, detail→category, browser tabiiy history. Direct detail URL ham site Back bilan categoryga qayta oladi.
- Unavailable product ko‘rsatilishi.
- Guest Save → Register → selected product avtomatik saqlanishi.
- Login qilingan user Save; yangi HTML sahifadan kelganda oldin silent refresh qilinib user guest deb noto‘g‘ri aniqlanmaydi. Login orqali kelgan pending Save ham avtomatik bajariladi.
- Favorites list va delete.
- Empty, loading, network-error va expired-auth holatlari.

### Deployment smoke tests
- HTTPS va HTTP→HTTPS redirect.
- `/api/v1/categories/` javobi.
- `/admin/` login.
- Product image `/media/` orqali ochilishi.
- `collectstatic` natijasi `/static/` orqali ochilishi.
- Birinchi TLS sertifikat olish (HTTP-only startup) va avtomatik renewal/reload jarayoni sinovi.
- Container healthchecks.

## 2. Minimal test runbook

Implementatsiya bosqichida loyiha uchun aniq buyruqlar README'ga yoziladi. Kutiladigan amaliyot:
- test suite'ni lokal Docker muhiti ichida bajarish;
- migration drift tekshiruvi;
- production image build;
- staging/EC2 smoke test;
- release oldidan `git diff` va secret scan ko‘rigi.

Test qilinmagan kodni testdan o‘tgan deb belgilamaslik kerak.

## 3. Health checks

- PostgreSQL: `pg_isready`.
- Backend readiness: `GET /health/`, DB aloqasining holatini minimal tekshirishi mumkin.
- Nginx: nginx process/endpoint tekshiruvi.

Health endpoint ichki konfiguratsiya, DB password yoki stack trace qaytarmaydi.

## 4. Logging

- Nginx access/error logs.
- Django application logs.
- Docker container stdout/stderr.
- Password, JWT, refresh cookie, CSRF secret yoki `.env` qiymatlari logga yozilmaydi.
- Docker log rotation/size limitlar sozlanadi.

## 5. Backup/restore

- PostgreSQL uchun `pg_dump` asosidagi backup.
- Uploaded media uchun alohida backup.
- Backup nusxasi EC2 instance/diskidan tashqarida saqlanadi.
- MVPda kunlik backup boshlang‘ich maqsad; real data yo‘qotish toleransi va restore vaqtiga qarab siyosat o‘zgartiriladi.
- Productionga chiqishdan oldin kamida bitta restore sinovi bajariladi.

## 6. Release checklist

- [ ] `DEBUG=False`; `ALLOWED_HOSTS` va trusted origins to‘g‘ri.
- [ ] Secretlar Git'da yo‘q.
- [ ] HTTPS faol va sertifikat yangilanishi sozlangan.
- [ ] DB/Gunicorn portlari public emas.
- [ ] Migrations backup va release rejasiga mos bajarilgan.
- [ ] Static/media fayllar ishlaydi.
- [ ] Auth/CSRF/JWT testlari o‘tgan.
- [ ] Favorites ownership/duplicate testlari o‘tgan.
- [ ] Admin CRUD tekshirilgan.
- [ ] Backup va restore yo‘riqnomasi mavjud.
- [ ] Browserda asosiy business flow tekshirilgan.
