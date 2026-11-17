# ADR-010: UZ/RU katalog va o‘zbekcha Django Admin

- **Holat:** Accepted — foydalanuvchi so‘ragan lokal MVP doirasi
- **Sana:** 2026-11-03

## Qaror

Category va Product o‘z ID/sluglarini, narx/rasm/mavjudlik/kategoriya aloqalarini
saqlaydi. Har biri uchun `language=uz|ru` bo‘lgan translation jadvali qo‘shiladi;
obyekt/til UNIQUE, qo‘llab-quvvatlangan til va bo‘sh bo‘lmagan matn CHECKlari DBda
tekshiriladi. Tarjima o‘chishi asosiy mahsulotni yoki Favoritesni o‘chirmaydi.

Eski UZ ustunlari moslik va `name,id` tartibi uchun asosiy manba bo‘lib qoladi.
Data migration ularni aynan UZ qatoriga nusxalaydi; eski ustunlar/IDlar/sluglar
o‘chirilmaydi. Oddiy `Category.save()`/`Product.save()` UZ nusxani shu transactionda
yangilaydi; UZ Translation.save() ham saqlangan qiymatni asosiy ustunlarga yozadi.
Admin foydalanuvchiga faqat bitta UZ maydonlar to‘plamini ko‘rsatadi. UZ matni
uchun `QuerySet.update`, `bulk_update`, `bulk_create` oddiy save sinxronlashini
chetlab o‘tadi: katalogni Admin orqali tahrirlash kerak. Yangi ommaviy yozish API
yoki umumiy xizmat/repository qatlami qo‘shilmaydi.

UZ majburiy. RU hali kiritilmagan holat ruxsat etiladi; Product RU nom/tavsif/
batafsil ma’lumoti birgalikda to‘ldiriladi. Mavjud RU tarjimasini o‘chirish
alohida belgini talab qiladi. Admin standart Django changeform transactionida
umumiy/UZ/RU ma’lumotni bitta obyekt sifatida saqlaydi. Qo‘llanma va ehtiyot
choralarini do‘kon mas’uli tekshiradi; avtomatik katalog tarjimasi yo‘q.

API tilini `?lang=uz|ru` tanlaydi. Parametrsiz avvalgi UZ maydonlar va javob
shakli saqlanadi; explicit parametr `language`, `translation_available` qo‘shadi.
RU yetishmasa tarjima matnlari `null`; UZ matniga yashirin fallback qilinmaydi.
Kategoriya va mahsulot tarjima holatlari alohida. Identifikator/narx/rasm/
mavjudlik/saqlangan sana o‘zgarmaydi. Ro‘yxatlar UZ nomi/ID tartibini saqlaydi.
RU querylar translationlarni prefetch qiladi; default query narxi o‘zgarmaydi.

Frontend qo‘lda yozilgan interfeys lug‘atidan foydalanadi. `herbalStore.language`
localStorage’da faqat tilni saqlaydi; JWT avvalgidek JS xotirada/HttpOnly cookie’da.
Til almashtirish joriy URLni reload qiladi, pending Save intenti va cookie saqlanadi.
Katalog matni hech qachon interfeys lug‘ati orqali tarjima qilinmaydi.

Admin har doim UZ; API tilini faqat explicit query tanlaydi. `Accept-Language`
default API yoki Adminni ruscha qilib qo‘ymaydi. Middleware CSRF/Origin, JWT,
cookie, permission va user scope qoidalarini o‘zgartirmaydi. Javobda
`Content-Language`, katalogda avvalgi `Cache-Control: no-store` qoladi.

## Lokal LAN va xavfsizlik — 2026-11-03

Redmi 15 bilan mavjud lokal qabul sinovini saqlash uchun Compose’dagi LAN
bog‘lanishi `WEB_LAN_IP` orqali aniq interfeysga beriladi. Joriy `wlo1` manzili
`10.178.150.236`; `.env.example` shu manzilga mos. O‘zgaruvchi belgilanmagan eski
sozlamalar uchun avvalgi `10.120.26.236` fallbacki saqlanadi. Veb porti localhost
va tanlangan LAN manziliga bog‘lanadi; `0.0.0.0` orqali barcha host interfeyslariga
ochilmaydi. PostgreSQL va Gunicorn portlari hostga chiqarilmaydi.

DHCP manzili o‘zgarsa faqat `WEB_LAN_IP`, `DJANGO_ALLOWED_HOSTS`dagi LAN hosti va
`DJANGO_CSRF_TRUSTED_ORIGINS`dagi uning aniq scheme/portli origini birga yangilanadi.
Localhost ruxsatlari va boshqa maxfiy sozlamalar saqlanadi. Bu CSRF/Origin
tekshiruvlarini o‘zgartirmaydi: token yo‘qligi yoki noto‘g‘ri Origin auth POSTini
avvalgidek rad etadi; wildcard va tashqi origin ruxsati kiritilmaydi. UZ/RU til
tanlovi shu siyosatdan mustaqil qoladi. Yangi environment/port uchun faqat
backend/web qayta yaratiladi; DB va volume’lar saqlanadi. Backup/migratsiya
preflighti va DHCPdan keyingi qo‘lda qabul tartibi
[qabul rejasida](../implementation/UZ-RU-ACCEPTANCE.md#4-redmi-15da-qolda-qabul-sinovi).

## Migratsiya chegarasi

Majburiy eski UZ matni bo‘sh bo‘lsa migratsiya atomik to‘xtaydi; kontent o‘ylab
topilmaydi, eski yozuv o‘chirilmaydi. Backup, restore sinovi va alohida foydalanuvchi
ruxsatidan oldin amaldagi bazaga migratsiya qo‘llanmaydi. Dev Compose source
mountlari/reloader sabab kod darhol ko‘rinishi mumkin; migratsiyasiz yangi Admin/RU
oqimiga o‘tish mumkin emas. Tartib [qabul rejasida](../implementation/UZ-RU-ACCEPTANCE.md).
