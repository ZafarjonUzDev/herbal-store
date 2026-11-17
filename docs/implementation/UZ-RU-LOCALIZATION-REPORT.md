# Herbal Store — UZ/RU lokalizatsiya va Django Admin hisoboti

Sana: 2026-11-03 (Asia/Samarkand).

## Joriy natija

Kod va avtomatik tekshiruvlar tayyor. Foydalanuvchining aniq ruxsatidan keyin
PostgreSQL/media backup olindi, yangi bazada restore va migratsiya tekshirildi,
so‘ng amaldagi `catalog.0002_catalog_translations` muvaffaqiyatli qo‘llandi.
Static fayllar yangilandi; sayt va o‘zbekcha Admin faol.
Haqiqiy RU kategoriya/mahsulot matnlari kiritilmadi; ruscha katalog kontenti
to‘liq tayyor deb hisoblanmaydi.

Mavjud yashil dizayn, Vanilla JS, oltita sahifa, JWT cookie/CSRF/Origin,
silent refresh, pending Save, bookmark, Favorites ownership va responsive
kartalar saqlandi. Yangi framework, tarjima xizmati yoki biznes moduli yo‘q.
8080 porti, `.secrets/dev-admin.json` va mavjud media saqlandi. Wi-Fi IP
`10.120.26.236`dan `10.178.150.236`ga o‘zgargani aniqlandi: Compose LAN bind
`WEB_LAN_IP` orqali boshqariladi, lokal `.env`da shu qiymat, ALLOWED_HOSTS va
CSRF origin moslashtirildi. Qolgan `.env` qiymatlari aynan saqlangani tekshirildi.
Backend/web qayta yaratildi, PostgreSQL konteyneri o‘zgarmadi. AWS boshlanmadi.

## Modellar va migratsiya

- CategoryTranslation: kategoriya, `language=uz|ru`, nom.
- ProductTranslation: mahsulot, `language=uz|ru`, nom, qisqacha tavsif,
  batafsil ma’lumot va qo‘llanma.
- Har ikkala jadvalda obyekt/til UNIQUE; qo‘llab-quvvatlangan til va
  bo‘sh bo‘lmagan majburiy matn CHECKlari bor. Translation FKlari CASCADE.
- Narx, rasm, mavjudlik, kategoriya, Product/Category ID va slug umumiy.
  Avvalgi PROTECT, Favorites CASCADE/UNIQUE va Decimal/CHECK saqlanadi.
- `0002_catalog_translations` eski UZ matnlarini aynan ko‘chiradi. Eski
  ustunlarni/yozuvlarni o‘chirmaydi; RU qatori yaratmaydi. Eski majburiy UZ
  matni bo‘sh bo‘lsa yashirin kontent yaratish o‘rniga atomik to‘xtaydi.
- Asl UZ ustunlari moslik va tartib uchun asosiy manba. Oddiy parent save
  UZ qatorini transaction ichida yangilaydi; UZ Translation.save ham saqlangan
  qiymatni originalga yozadi. UZ matni uchun bulk ORM update/create ishlatmang:
  ular model save sinxronlashini chetlab o‘tadi. Admin orqali tahrirlang.

## Django Admin

Standart Django Admin CRUD, rasm previewi, filtr, qidiruv va slug avtomatik
to‘ldirish saqlangan. Alohida dashboard qo‘shilmadi.

- Umumiy: slug, kategoriya aloqasi, rasm/preview, Decimal narx va mavjudlik.
- O‘zbekcha (UZ): kategoriya/mahsulot nomi; mahsulot tavsifi va qo‘llanma.
- Ruscha (RU): shu matn maydonlarining qo‘lda kiritiladigan variantlari.
- Yangi RU blok bo‘sh qolishi mumkin; Product RU maydonlari birgalikda
  to‘ldiriladi. Qisman tarjima validatsiyada rad etiladi. Mavjud RU tarjimani
  o‘chirish alohida belgilashni talab qiladi.
- Bitta forma bitta parent obyekt va tegishli tarjimalarni transactionda
  saqlaydi. Listda RU kiritilgan/kiritilmagan holati ko‘rinadi.
- UZ gettext katalogi: 358 ta Django Admin/Auth/SimpleJWT interfeys yozuvi;
  djangojs: 88 ta yozuv. `.po` manbalari bilan `.mo` fayllari mavjud.
  User/Group permission tanlovlari ham UZ; DB permission ID/nomlari o‘zgarmaydi.

## Sayt va API til tanlovi

`frontend/js/i18n.js` qo‘lda yozilgan UZ/RU interfeys lug‘ati. Standart UZ;
headerdagi tanlov `herbalStore.language` orqali saqlanadi. Faqat til
localStorage’da; access JWT avvalgidek JS xotirada, refresh HttpOnly cookie’da.
Til almashtirish URLni saqlab reload qiladi; pending Save va auth cookie
saqlanadi. Browser Back/boshqa tabdagi til o‘zgarishi ham hisobga olinadi.

Catalog/Favorites GET `?lang=uz|ru` ishlatadi. Explicit parametr `language` va
`translation_available` qaytaradi; parametrsiz eski UZ javob shakli saqlanadi.
RU yetishmasa tarjima matnlari `null` va UI aniq yetishmagan tarjima holatini
ko‘rsatadi. Category/Product holati mustaqil. Umumiy narx, ID, slug, rasm va
Save ishlayveradi. Katalog matni interfeys lug‘atiga yuborilmaydi.

Admin har doim UZ; `Accept-Language` default API/Admin tilini o‘zgartirmaydi.
API `Content-Language` va avvalgi `no-store` siyosati saqlangan. RU querylari
prefetch qiladi; default Favorites GET avvalgi bitta query chegarasida qoladi.

## Test natijalari

Muhit: lokal Python 3.12.2, Django 5.2.18, PostgreSQL 18 va haqiqiy headless
Chrome. Qo‘shimcha ravishda amaldagi konteynerning Python 3.13.15/PostgreSQL
16.15 muhitida ham yangi noyob test bazasida suite bajarildi. Barcha test
bazalari asosiy bazadan alohida; asosiy baza reset qilinmadi.

| Tekshiruv | Natija |
|---|---|
| O‘zgarishlardan oldingi snapshot regression | 80/80 Django PASS |
| Yakuniy Django regression | **107/107 PASS**, 8.701 soniya |
| Haqiqiy backup restore + migratsiyadan keyingi regression | **107/107 PASS**, 8.803 soniya |
| Amaldagi Python 3.13.15/PostgreSQL 16.15, alohida test bazasi | **107/107 PASS**, 14.289 soniya |
| Django check | PASS, 0 muammo |
| Migration drift | PASS, No changes detected |
| Yangi migratsiyalar, izolyatsiyalangan PostgreSQL | PASS |
| Eski matn/ID/slug/rasm/user/Favorites migratsiya testi | PASS, test bazasida |
| Admin UZ/RU CRUD, qisman RU, rollback, preview | PASS |
| API default UZ/explicit UZ/RU/yo‘q RU; ownership/query chegaralari | PASS |
| Accounts CSRF/Origin/JWT/rotation/blacklist/logout regressionlari | PASS |
| OpenAPI validate/fail-on-warn | PASS |
| pip check | PASS |
| Chrome frontend mock regression | **41/41 PASS** |
| Til almashtirish/reload, login va registration pending Save | PASS, mock API bilan |
| UZ/RU katalog/Favorites, 280–1600px | **44 responsive ssenariy PASS** |
| Haqiqiy Chrome + Django API, yangi PostgreSQL bazasi | **PASS**, mock ishlatilmagan |
| Haqiqiy login va register pending Save, til/reload, bookmark/Favorites/logout | PASS |
| Haqiqiy native Admin UZ/RU Category/Product CRUD, qisman RU rollback, rasm preview | PASS |
| Haqiqiy UZ/RU katalog 390/1024/1440px | PASS, rasmlar saqlangan |
| Amaldagi migratsiya va restartdan keyingi asl fingerprintlar | PASS — 4 kategoriya, 6 mahsulot, 10 user, 8 Favorites |
| Amaldagi UZ translationlar | PASS — 4/6 qator, matnlar aynan teng; RU 0/0 |
| Amaldagi barcha media hashlar | PASS — 7 fayl, 6 mahsulot rasmi mavjud |
| Localhost va joriy LAN HTTP, Admin/static/media/OpenAPI/API | PASS — 63 + 63 = 126 ta GET |
| Joriy LAN bind, host va CSRF/Origin | PASS — yangi IP, valid CSRF/no refresh cookie 401; untrusted Origin 403 |
| Python AST | PASS, 63 Python fayli |
| Editorconfig whitespace | PASS, 69 bo‘sh bo‘lmagan source fayli |

Dastlabki 107-testli urinishda bitta yangi test JSON o‘rniga multipart yuborib,
`product_id`ni matnga aylantirdi va kutilgan 200 o‘rniga to‘g‘ri 400 oldi.
Test `format='json'` bilan tuzatildi; yakuniy suite 107/107 o‘tdi. Paketlar
yetishmagan dastlabki lokal check va sandbox socket/tarmoq cheklovlari sabab
to‘xtagan urinishlar PASS deb hisoblanmadi; mavjud requirements paketlari
o‘rnatilib, tekshiruvlar alohida PostgreSQLda qayta bajarildi.

Haqiqiy Chrome runnerida ham ikkita test-harness taxmini tuzatildi: parametrsiz
API metadata qo‘shmasligi va `/admin/` login sahifasiga redirect qilishi.
Yakuniy haqiqiy API/Admin brauzer tekshiruvi exit 0 bilan tugadi. Bu tuzatishlar
ilovaning xatti-harakatini almashtirmadi. Barcha browser yozuvlari yangi test
bazasida; `.secrets` yoki amaldagi bazadan credential olinmadi.

Takrorlash: `.venv/bin/python scripts/check_localization.py --browser --keep-data`.
Yakuniy browser urinishida avval o‘tgan to‘liq suite takrorlanishi o‘rniga
`--label apps.accounts.tests.test_configuration` bilan 4 configuration testi,
check/drift/migrate/OpenAPI/pip va barcha haqiqiy browser oqimlari bajarildi.

Ruff/Black alohida o‘rnatilmagan; ular bilan tekshirildi deb da’vo qilinmaydi.
Sintaksis, mavjud formatlash qoidalari va haqiqiy JS browser execution tekshirildi.

Dalillar: boshlang‘ich kod `/tmp/herbal-store-before-uz-ru.tar.gz`,
baseline cluster `/tmp/herbal-localization-rs3vgr0a`, yakuniy backend cluster
`/tmp/herbal-localization-63yu_dzn`. Vaqtinchalik klasterlar tekshiruvdan so‘ng
to‘xtatilgan; bu kataloglar amaldagi DB backupi o‘rnini bosmaydi.
Haqiqiy Chrome rasmlari `/tmp/herbal-localization-ubs9ieo_/browser/` ichida:
`catalog-{uz,ru}-{390,1024,1440}.png` va `admin-product-uz-ru.png`.

## O‘zgartirilgan fayllar

- `backend/apps/catalog/`: models, admin, serializers, views; yangi
  `localization.py`, `migrations/0002_catalog_translations.py`,
  `tests/test_translation_models.py`, `tests/test_localization_api.py`;
  yangilangan `tests/test_admin.py`.
- `backend/apps/favorites/{serializers,views}.py`: tanlangan tilda joriy
  Product/Categoryni ko‘rsatish va prefetch.
- `backend/apps/accounts/admin.py`: User/Group ruxsatlarining UZ yorliqlari.
- `backend/config/settings.py`, yangi `middleware.py`: til siyosati va locale.
- `backend/locale/uz/LC_MESSAGES/{django,djangojs}.{po,mo}`.
- `frontend/js/{api,app,navigation}.js`, yangi `i18n.js`;
  `frontend/css/styles.css`, `login.html`, `register.html`.
- `frontend/tests/{fixture,regression}.js`, yangi `localization_smoke.py`.
- Yangi `scripts/{check_localization,catalog_integrity,localization_browser}.py`.
- `docker-compose.yml`, `.env.example`: aniq LAN IP uchun `WEB_LAN_IP`.
  Lokal `.env`ning faqat `WEB_LAN_IP`, `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_CSRF_TRUSTED_ORIGINS` qiymatlari yangilandi; secretlar chiqarilmadi.
- README; architecture 03/04/06/07/12, yangi ADR-010;
  ushbu hisobot va `UZ-RU-ACCEPTANCE.md`.

## Backup, amaldagi yangilanish va qolgan qo‘lda tekshiruv

Backup: `/home/zafarjon/herbal-store-backups/2026-11-03-uz-ru`.
Katalog `0700`, fayllar `0600`. PostgreSQL dump 62 579 bayt, media arxivi
57 667 bayt. SHA256SUMS, archive listing, 7 media faylining path/hajm/hash
manifesti va barcha 6 Product.image yo‘li tekshirildi. Nusxa alohida
`/tmp/herbal-localization-40inpwco` klasteriga tiklandi; asl ma’lumotlar
migratsiya oldi/keyin aynan teng, 107/107 test hamda OpenAPI PASS.

Amaldagi migratsiyadan oldin backupdan keyin yozuvlar o‘zgarmagani tekshirildi;
faqat `catalog.0002` pending edi. Migratsiya, collectstatic va restartdan keyin
ham asl UZ matni/ID/slug/rasm/narx/mavjudlik/timestamps/user/Favorites hashlar
teng. UZ translationlar asl matnga aynan teng, RU yaratilmagan. PostgreSQL
konteyneri saqlandi; volume o‘chirish yoki asosiy bazaga restore bajarilmadi.

Eski LAN IP joriy Wi-Fi interfeysida yo‘q edi. `WEB_LAN_IP=10.178.150.236`
va mos host/origin qo‘llandi; `.env`ning oldingi nusxasi shu yopiq backupda.
Web faqat localhost va aniq joriy Wi-Fi IPga bog‘lanadi. Backend/web yangi
sozlamalarni yuklash uchun qayta yaratildi. DHCP IP yana o‘zgarsa `.env`dagi
shu uch qiymatni moslashtirish kerak; CSRF/Origin himoyasi saqlanadi.
Yangi sozlamadan keyin ham barcha uch servis healthy, DB konteyner IDsi
o‘zgarmagan va 4/6/10/8 asl yozuv fingerprintlari teng. Localhost hamda LAN
Host uchun haqiqiy CSRF tokenli so‘rov tekshirildi: bir xil Origin/no refresh
cookie → 401, noto‘g‘ri Origin → 403. Ushbu auth tekshiruvlari user/Favorites
yozuvlarini yaratmagan yoki o‘zgartirmagan.
Joriy ikkala haqiqiy HTTP URL bo‘yicha 63 tadan GET tekshiruvi ham PASS:
6 sahifa, frontend assetlar, o‘zbekcha Admin login va 8 static asset,
4 kategoriya/6 mahsulot UZ/RU API, 6 rasm, health va OpenAPI. Ikkala hostdagi
ID/slug/narx/mavjudlik va rasm yo‘llari mos. Yangi LAN health alohida curl
so‘rovi bilan ham `{"status":"ok"}` qaytardi.

Do‘kon mas’ullari barcha RU kategoriya/mahsulot nomlari, tavsif va qo‘llanmalarni
qo‘lda kiritib tekshiradi. Iste’mol tartibi, cheklovlar va ehtiyot choralari
UZda ham, RUda ham tasdiqlanishi kerak. Avtomatik/AI katalog tarjimasi qilinmadi.

Noutbuk: http://127.0.0.1:8080/ . Redmi 15: shu lokal tarmoqda
http://10.178.150.236:8080/ . Admin: `/admin/`. Til/reload/Guest Save → login
va register/Favorites/logout/preview/CRUD qabul tartibi
[UZ-RU-ACCEPTANCE.md](UZ-RU-ACCEPTANCE.md)da. Chrome emulyatsiyasi jismoniy
Redmi 15 sinovi o‘rnini bosmaydi; bu sinov hali foydalanuvchi bilan bajariladi.
