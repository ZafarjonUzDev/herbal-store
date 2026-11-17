# Herbal Store — UZ/RU qabul sinovi va xavfsiz migratsiya rejasi

Sana: 2026-11-03. Ushbu hujjat bajarish tartibini beradi; undagi buyruqlar
o‘z-o‘zidan bajarilgan yoki ruscha mahsulot kontenti tasdiqlangan deb hisoblanmaydi.

## 1. Amaldagi bazaga tegmasdan avtomatik tekshiruv

2026-11-03dagi boshlang‘ich regression: o‘zgarishlardan oldingi
`/tmp/herbal-store-before-uz-ru.tar.gz` kod nusxasi
`/tmp/herbal-store-baseline-uz-ru`ga ochilib, yangi PostgreSQL 18 klasterida
tekshirildi. Django **80/80 PASS** (7.950 soniya), `check` — 0 muammo,
migration drift — yo‘q, asl migratsiyalar — PASS, OpenAPI — PASS,
`pip check` — PASS. Klaster `/tmp/herbal-localization-rs3vgr0a` to‘xtatildi;
amaldagi PostgreSQLga migratsiya qo‘llanmadi. Bu boshlang‘ich natija;
yakuniy lokalizatsiya natijalari alohida hisobotda keltiriladi.

Yakuniy texnik tekshiruv: yangi PostgreSQL 18 klasterida **107/107 Django testi
PASS** (8.594 soniya), check/drift/migrations/OpenAPI/pip check — PASS. Haqiqiy
Chrome integratsiyasi ham izolyatsiyalangan bazada, mock APIsiz bajarildi:
Guest Save → til almashtirish/reload → login; alohida registration → pending Save;
bookmark/Favorites qo‘shish-o‘chirish; HttpOnly cookie va memory token chegaralari;
RU matn mavjud/yo‘q holatlari; UZ/RUda 390/1024/1440px; native Admin kategoriya va
mahsulot CRUD, qisman RU formani atomar rad etish va rasm preview — **PASS**.
Sinovdagi RU matnlar faqat umumiy dastur fixturelari bo‘lib, dorivor qo‘llanma emas.
Browser harnessidagi ikki taxmin (default API metadata va Admin login redirect)
tuzatildi; yakuniy ishga tushirish exit 0. So‘nggi qayta tekshiruv butun suite’ni
takrorlash o‘rniga 4 ta konfiguratsiya testi va to‘liq browser integratsiyasini
bajardi. Server va vaqtinchalik PostgreSQL to‘xtatildi. Screenshotlar:
`/tmp/herbal-localization-ubs9ieo_/browser/` (`catalog-uz/ru-390/1024/1440.png`,
`admin-product-uz-ru.png`). Jismoniy Redmi 15 hali qo‘lda tekshirilishi kerak.

Loyiha ildizidan:

```bash
.venv/bin/python scripts/check_localization.py --keep-data
```

Haqiqiy Chrome/frontend/API/Admin integratsiyasini ham qo‘shish:

```bash
.venv/bin/python scripts/check_localization.py --browser --keep-data
```

`--browser` faqat yangi, bo‘sh vaqtinchalik bazada umumiy sinov yozuvlarini yaratadi.
U `--restore-dump` bilan birga qabul qilinmaydi; asosiy `.secrets` o‘qilmaydi.

Skript `/tmp/herbal-localization-*` ichida yangi PostgreSQL klasteri yaratadi,
faqat `127.0.0.1`dagi bo‘sh portda ishlatadi va yangi, alohida bazaga migratsiya
qo‘llaydi. Django testlari ham shu klasterning alohida test bazasida ishlaydi.
Amaldagi `.env` o‘qilmaydi; test secret va ulanish sozlamalari alohida beriladi.
Media va static natijalari ham vaqtinchalik katalogga yoziladi. Yakunda faqat
ushbu vaqtinchalik klaster to‘xtatiladi. `--keep-data` diagnostika fayllarini
saqlaydi; shu parametrsiz faqat skript yaratgan vaqtinchalik katalog tozalanadi.

Tekshiruvlar: Django `check`, `makemigrations --check --dry-run`, izolyatsiyalangan
`migrate`, to‘liq Django suite, `spectacular --validate --fail-on-warn`, `pip check`.
PostgreSQL server binarylari va loyihaning mavjud pin qilingan Python paketlari
kerak. Zarur bo‘lsa `--postgres-bin /usr/lib/postgresql/18/bin` yoki
`--python /path/to/venv/bin/python` ko‘rsatiladi. Skript asosiy bazani reset qilmaydi.

Frontend mock regressionlari:

```bash
python3 scripts/browser_smoke.py --regression-only
```

Bu rejim yangi foydalanuvchi yoki katalog yozuvi yaratmaydi. To‘liq browser smoke
esa yangi test foydalanuvchisini yaratadi va mavjud lokal Admin credentialini
o‘qishi mumkin; uni asosiy bazada qabul sinovisiz ishga tushirmang. To‘liq oqimlar
izolyatsiyalangan test muhiti yoki quyidagi ongli qo‘lda qabul sinovi orqali tekshiriladi.

## 2. Backup va amaldagi migratsiya uchun alohida ruxsat

**Amaldagi PostgreSQLga migratsiya qo‘llashdan oldin foydalanuvchining aniq ruxsati
olinadi.** Kod backupi PostgreSQL backupi o‘rnini bosmaydi. Backupning joyi,
maxfiyligi, tekshirish natijasi va migratsiya ro‘yxati ko‘rsatilgach ruxsat so‘raladi.

Ruxsat so‘rash uchun konkret reja:

1. Admin orqali katalog tahrirlash, rasm yuklash va qabul sinovi yozuvlarini
   vaqtincha to‘xtatib turish; servislarni to‘xtatmasdan izchil nusxa olish.
2. Repo tashqarisida faqat egasi o‘qiydigan katalogga PostgreSQL `pg_dump -Fc`
   va barcha `/app/media` fayllari arxivini olish. `.env` yoki parol terminalga
   chiqarilmaydi. Dump foydalanuvchi ma’lumotlari/parol hashlarini ham o‘z ichiga
   olgani uchun unga maxfiy backup sifatida munosabat qilinadi.
3. Arxivlar bo‘sh emasligini, SHA256 qiymatlarini va `pg_restore --list`ni tekshirish.
   Nusxani alohida disk yoki foydalanuvchi tanlagan himoyalangan joyga ko‘chirish.
4. Dumpni faqat yangi izolyatsiyalangan PostgreSQLga tiklash; shu nusxaga yangi
   migratsiyalarni qo‘llash, regressionlarni bajarish va oldin/keyin fingerprintlarni
   tenglashtirish. Asosiy bazaga restore qilinmaydi.
5. Restore sinovi, UZ majburiy maydonlar preflighti va avtomatik tekshiruvlar
   o‘tgach, foydalanuvchining ruxsati amaldagi bazaga aynan yangi migratsiyani
   qo‘llashni ham qamrab olishini tekshirish. Backup → muvaffaqiyatli restore →
   migratsiya rejasi birga tasdiqlangan bo‘lsa qayta ruxsat so‘ralmaydi.
   Shundan so‘ng live fingerprintni saqlash, migratsiya,
   fingerprint taqqoslash, static chiqarish va brauzer qabul sinovi bajariladi.

Quyidagi buyruqlar **reja namunasi**; backup katalogi va ruxsat tasdiqlanmaguncha
bajarilmaydi. Muhitda boshqa loyihalar ham bor; faqat Herbal Store Compose fayllari
va xizmatlari ishlatiladi. `docker compose config` orqali real secretlarni chiqarmang.

```bash
umask 077
HERBAL_BACKUP_DIR=/home/zafarjon/herbal-store-backups/2026-11-03-uz-ru
mkdir -p /home/zafarjon/herbal-store-backups
mkdir -m 700 "$HERBAL_BACKUP_DIR"

docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python < scripts/catalog_integrity.py > "$HERBAL_BACKUP_DIR/integrity-before.json"

docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > "$HERBAL_BACKUP_DIR/database.dump"

docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend tar -C /app -czf - media > "$HERBAL_BACKUP_DIR/media.tar.gz"

pg_restore --list "$HERBAL_BACKUP_DIR/database.dump" > "$HERBAL_BACKUP_DIR/archive-list.txt"
tar -tzf "$HERBAL_BACKUP_DIR/media.tar.gz" > "$HERBAL_BACKUP_DIR/media-list.txt"
sha256sum "$HERBAL_BACKUP_DIR/database.dump" "$HERBAL_BACKUP_DIR/media.tar.gz" > "$HERBAL_BACKUP_DIR/SHA256SUMS"

.venv/bin/python scripts/check_localization.py --restore-dump "$HERBAL_BACKUP_DIR/database.dump" --keep-data
```

Har bir buyruqning exit kodi tekshiriladi; xato bo‘lsa keyingi bosqich bajarilmaydi.
Backup katalogi mavjud bo‘lsa ustiga yozilmaydi; yangi noyob katalog tanlanadi.
`pg_restore --list`ning o‘zi haqiqiy restore sinovi emas. `--restore-dump` bo‘sh,
yangi test bazasiga tiklaydi, migratsiya oldidan/keyin aynan shu bazaning
fingerprintlarini taqqoslaydi va regressionlarni bajaradi. Media arxivi alohida
vaqtinchalik katalogga ochilib, rasmlar mavjudligi ham tekshirilishi kerak.

`catalog_integrity.py` bitta `REPEATABLE READ, READ ONLY` transactionda asl UZ
nom/tavsif/qo‘llanma, kategoriya va mahsulot ID/sluglari, kategoriya aloqalari,
narx/mavjudlik/rasm yo‘llari, foydalanuvchilar va Favorites aloqalarining soni va
SHA256 hashlarini qaytaradi. Matnlar, parollar va shaxsiy ma’lumotlar chiqmaydi.
`legacy_required_blank_counts`dagi barcha qiymatlar nol bo‘lishi kerak. Muammo
topilsa asl yozuvni yashirincha to‘ldirish/o‘chirish o‘rniga mas’ul administrator
bilan tuzatiladi, so‘ng yangi backup olinadi.

**Muhim:** `backend/entrypoint.sh` birinchi argument `gunicorn` bo‘lganda avtomatik
`migrate` bajaradi. Shu sabab ruxsat va tekshirilgan backupdan oldin amaldagi
backendni restart/recreate yoki odatiy Compose startup bilan ishga tushirmang.
Volume o‘chirish, `down -v`, prune, reset va amaldagi bazaga restore bu rejaga kirmaydi.

## 3. Noutbukda qo‘lda qabul sinovi

Amaldagi baza migratsiyasi tasdiqlanib bajarilgandan keyin:

- Sayt: http://127.0.0.1:8080/
- Kategoriya namunasi: http://127.0.0.1:8080/category.html?slug=demo-choylar
- Mahsulot namunasi: http://127.0.0.1:8080/product.html?slug=demo-limon-oti
- Saqlanganlar: http://127.0.0.1:8080/favorites.html
- Kirish: http://127.0.0.1:8080/login.html
- Ro‘yxatdan o‘tish: http://127.0.0.1:8080/register.html
- Admin: http://127.0.0.1:8080/admin/
- OpenAPI: http://127.0.0.1:8080/api/schema/
- Frontend regression: http://127.0.0.1:8080/tests/index.html

Namuna slug mavjud bo‘lmasa bosh sahifadagi haqiqiy kategoriya va mahsulot orqali
kiring; mavjud slugni test uchun almashtirmang.

1. Yangi brauzer profilida sayt UZda ochilishini tekshiring. Headerdagi RUni
   tanlang; navigatsiya, footer, kategoriya/karta/detail, mavjudlik, narx birligi,
   loading/bo‘sh holat/xato, login/register va Saqlanganlar matnlari ruscha bo‘lsin.
   Saytni qayta yuklang va boshqa sahifaga o‘ting: tanlangan til saqlansin.
2. RU bazaviy kontenti hali kiritilmagan mahsulotda yetishmagan tarjima aniq
   ko‘rsatilsin; UZ qo‘llanma ruscha tarjima sifatida berilmasin. UZga qaytganda
   asl matnlar to‘liq ko‘rinsin. Product ID, slug, narx, rasm, mavjudlik va kategoriya
   aloqasi til almashtirish bilan o‘zgarmasin.
3. Guest bo‘lib Saqlashni bosing → Kirishga o‘ting → test akkaunt bilan kiring.
   Tanlangan mahsulot avtomatik bir marta saqlansin. Alohida oqimda ro‘yxatdan
   o‘tish orqali ham takrorlang. Noto‘g‘ri parol va bo‘sh majburiy maydon xabarlari
   tanlangan tilda bo‘lsin; xatodan so‘ng pending Save saqlansin.
4. `Saqlash ↔ Saqlangan` tugmasini, Saqlanganlar ro‘yxatini va o‘chirishni tekshiring.
   Reload, yangi sahifa va til almashtirishda akkaunt va bookmark holati tiklansin.
   Bekor/Back bilan auth oqimidan chiqilsa eski pending Save bajarilmasin.
5. Chiqish tasdiqlash oynasida UZ/RU matn, Bekor qilish, tasdiqlash, klaviatura
   va fokus qaytishini tekshiring. Bekor qilishda login holati saqlansin.
6. Adminni oching. Umumiy, O‘zbekcha va Ruscha formalar, UZ sarlavha/menyu/amallar,
   filtr/qidiruv, validatsiya, ruxsatlar va rasm previewini tekshiring. CRUDni
   izolyatsiyalangan test muhiti yoki ataylab yaratilgan test yozuvlarida bajaring;
   haqiqiy mahsulotni tekshirish uchun o‘chirmang. Bitta saqlash bitta mahsulot IDsi
   ostida UZ/RU matnlarni saqlasin. Qisman RU forma rad etilsin; butunlay bo‘sh RU
   blok hali kiritilmagan tarjima holati sifatida ishlasin.
7. Desktop 1024pxda 4, 1440pxda 5 ustun; 320–390pxda 2 ustun, vertikal kartalar,
   uzun UZ/RU nomlar va tugmalar sig‘ishini tekshiring. Header/til tugmalari,
   detail qo‘llanmasi, auth formalar va logout oynasi yon tomonga siljimasin.

API uchun default `GET /api/v1/categories/` UZ va avvalgi javob kalitlarini saqlaydi;
til/translation metadata uchun `?lang=uz` yoki `?lang=ru` aniq ko‘rsatiladi. RU uchun
`GET /api/v1/categories/?lang=ru`, kategoriya mahsulotlari va product detailida
ham shu mexanizm ishlatiladi. Javobdagi til/translation holatini, RU mavjud va
yo‘q obyektlarni tekshiring. Narx va umumiy IDlar o‘zgarmasin.

## 4. Redmi 15da qo‘lda qabul sinovi

Noutbuk va Redmi 15 bir xil lokal tarmoqda bo‘lsin. 2026-11-03da aniqlangan
`wlo1` Wi-Fi interfeysining manzili `10.178.150.236`; joriy LAN URL:
http://10.178.150.236:8080/ . Avvalgi `10.120.26.236` manzili ushbu interfeysda
endi mavjud emas. Noutbukdagi http://127.0.0.1:8080/ telefon uchun noutbuk
manzili emas. Compose veb portini `127.0.0.1` va `.env`dagi `WEB_LAN_IP`
ko‘rsatgan aniq LAN interfeysiga bog‘laydi; barcha interfeyslarga ochmaydi.

Chrome’da LAN URLni oching va 3-bo‘limdagi UZ/RU, reload, guest Save → login va
register, Favorites, logout va Back oqimlarini takrorlang. Portret hamda landshaftda
til tanlagich, 2 ustunli kartalar, detail matni va klaviatura ochilgan formalarni
tekshiring. Noutbukdagi login cookie telefon yoki boshqa host bilan bo‘lishilmaydi;
telefon brauzerida alohida kiring. Noutbuk/telefon orasidagi Favorites yozuvlari
bir akkaunt bilan API’dan qayta o‘qilganda mos bo‘lsin.

Natijaga brauzer/qurilma, URL, sana va topilgan xatoni yozing. Chrome emulyatsiyasi
jismoniy Redmi sinovi o‘rnini bosmaydi.

DHCP yoki Wi-Fi tarmog‘i sabab LAN IP yana o‘zgarsa:

1. `ip -brief -4 address show wlo1` bilan joriy Wi-Fi manzilini aniqlang.
   Docker bridge manzillarini telefon uchun ishlatmang.
2. Maxfiy `.env` ichida faqat `WEB_LAN_IP`, `DJANGO_ALLOWED_HOSTS`dagi LAN
   manzili va `DJANGO_CSRF_TRUSTED_ORIGINS`dagi unga mos `http://IP:8080`
   originini yangilang. `localhost`/`127.0.0.1` qiymatlari va boshqa sozlamalarni
   saqlang. `0.0.0.0`, wildcard host/origin yoki CSRF himoyasini o‘chirish kerak emas.
   `.env`ni terminalga yoki Git’ga chiqarmang.
3. `backend` entrypointi avtomatik migratsiya bajarishini hisobga olib, 2-bo‘limdagi
   backup va migration tekshiruvlari bajarilganini tasdiqlang. So‘ng faqat Herbal
   Store `backend` va `web` xizmatlarini mavjud image’lardan qayta yarating:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --no-build --force-recreate backend web
   ```

   Oddiy `restart` yangi environment va port bog‘lanishini yuklamaydi. `db`
   xizmati va volume’lariga tegmang. Backend va Nginx birga qayta yaratilishi
   Nginx upstreamining eski konteyner IPsida qolishini ham oldini oladi.
4. Ikkala URLda `/health/`, katalog, mahsulot rasmi va Adminni tekshiring.
   Auth POSTlari yangi manzilda ham CSRF tokeni va to‘g‘ri Origin talab qilishi
   kerak. So‘ng telefonda yangi LAN URL bilan yuqoridagi qabul sinovini takrorlang.

## 5. Kontentni tasdiqlash sharti

Ruscha mahsulot/kategoriya matnlari avtomatik tarjima qilinmaydi. Do‘kon mas’ullari
RU nom, tavsif, batafsil ma’lumot va qo‘llanmani Admin orqali qo‘lda kiritadi.
Iste’mol tartibi, cheklov va ehtiyot choralari har ikki tilda mas’ul shaxs tomonidan
tekshiriladi. Zarur RU matnlar kiritilib tasdiqlanmaguncha ruscha katalog kontenti
to‘liq tayyor deb qabul qilinmaydi; interfeysning RUda ishlashi alohida natijadir.

## 6. 2026-11-03dagi amaldagi migratsiya natijasi

Foydalanuvchi backup → izolyatsiyalangan restore → tekshiruvdan so‘ng amaldagi
migratsiya rejasiga aniq ruxsat berdi. PostgreSQL va media nusxalari repo tashqarisidagi
`/home/zafarjon/herbal-store-backups/2026-11-03-uz-ru` katalogiga olindi:
katalog `0700`, backup fayllari `0600`. Dump haqiqiy alohida PostgreSQLga tiklandi,
`catalog.0002_catalog_translations` tekshirildi va **107/107 Django testi PASS**.
Media arxividagi barcha 7 faylning hajmi va SHA256 qiymati manifestga mos.

Shundan keyin amaldagi `catalog.0002_catalog_translations` qo‘llandi. Oldin/keyin
fingerprintlar teng: 4 kategoriya, 6 mahsulot, 10 foydalanuvchi va 8 Favorites
yozuvi, jumladan ID/sluglar, asl UZ matnlar va aloqalar saqlandi. UZ translationlar
4/6 bo‘lib, asl matnlarga aynan teng; RU translationlar hozircha **0**. Static
yangilandi. Wi-Fi IP o‘zgargani sabab yuqoridagi aniq LAN bog‘lanishi va unga mos
host/originlar yangilandi; faqat backend/web qayta yaratildi, DB konteyneri va
volume’lari saqlandi. Backend, web va DB healthy; yangi LAN uchun ham CSRF/Origin
talablari saqlangani tekshirildi. RU katalog kontenti va jismoniy Redmi 15 qabul
sinovi yuqoridagi tartib bo‘yicha mas’ullar tomonidan yakunlanadi.

Yakuniy tashqi HTTP tekshiruvi: localhost va joriy LAN URLning har birida
63 tadan, jami **126 GET PASS**. Sahifalar, UZ Admin, static/media, OpenAPI,
default UZ/explicit UZ/RU va barcha 6 mahsulotning umumiy qiymatlari mos.
Amaldagi Python 3.13.15/PostgreSQL 16.15 muhitida yangi noyob test bazasida
ham **107/107 PASS** (14.289 soniya). Asosiy bazada test yozuvi yaratilmagan.
