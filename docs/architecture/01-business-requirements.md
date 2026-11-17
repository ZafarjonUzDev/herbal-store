# 01 — Business Requirements

## 1. Mahsulot ta’rifi

Herbal Store — Toshkent shahridagi dorivor giyohlar va boshqa tabiiy mahsulotlar do‘koni uchun public web-katalog. MVP faqat Toshkentdagi bosh do‘konni ko‘rsatadi; boshqa viloyat yoki mamlakat filiallarini boshqarish scope'da yo‘q.

Sayt xarid qilish yoki yetkazib berish tizimi emas. Mijoz mahsulot haqidagi ma’lumotni masofadan ko‘radi, xaridni esa do‘konning o‘zida qiladi.

## 2. Biznes muammo

Mijozlar mahsulotning mavjudligi, narxi, ko‘rinishi yoki batafsil ma’lumoti haqida telefon orqali qayta-qayta so‘rashi mumkin. Toshkentdan uzoqda yashovchi mijoz faqat ma’lumot olish uchun safar qilishga majbur bo‘lishi mumkin.

## 3. Maqsad

- Mijozga mahsulotning rasmi, nomi, narxi, mavjudligi va do‘kon tasdiqlagan batafsil ma’lumotini onlayn ko‘rsatish.
- Takroriy oddiy qo‘ng‘iroqlarni kamaytirishga yordam berish.
- Mijozga yoqtirgan mahsulotlarini shaxsiy ro‘yxatga saqlash imkonini berish.
- Admin uchun mahsulot va kategoriyalarni bir joydan boshqarish.

## 4. Aktorlar

### Guest (ro‘yxatdan o‘tmagan tashrif buyuruvchi)
- Kategoriyalar ro‘yxatini ko‘radi.
- Kategoriyani ochib, unga tegishli mahsulotlarni ko‘radi.
- Mahsulot tafsilotini ko‘radi.
- Saqlash tugmasini bosganda registration sahifasiga yo‘naltiriladi.

### Registered customer
- Guestning barcha amallarini bajaradi.
- Username va password bilan login qiladi.
- Mahsulotni saqlaydi.
- O‘zining saqlangan mahsulotlarini ko‘radi.
- Saqlangan mahsulotni ro‘yxatdan olib tashlaydi.

### Administrator
- Django Admin orqali Category va Product yaratadi, ko‘radi, yangilaydi va o‘chiradi.
- Mahsulot narxi, rasmi, ma’lumoti va mavjudlik holatini boshqaradi.

## 5. Asosiy foydalanuvchi oqimi

1. Brauzerda sayt ochiladi va kategoriyalar ko‘rsatiladi.
2. Kategoriya tanlanadi; o‘sha kategoriyadagi mahsulotlar ko‘rsatiladi.
3. Mahsulot tanlanadi; detail sahifada nomi, rasmi, narxi, mavjudligi, tavsifi va batafsil axboroti ko‘rsatiladi.
4. Guest `Saqlash`ni bossa, ro‘yxatdan o‘tish sahifasi ochiladi. Muvaffaqiyatli registrationdan keyin oldindan tanlangan mahsulot alohida Favorites API orqali avtomatik saqlanadi.
5. Avval ro‘yxatdan o‘tgan, ammo hozir login qilmagan mijoz ham login formasini tanlashi mumkin. Login yoki registrationdan keyin avval tanlangan mahsulot alohida Favorites API orqali saqlanadi. Login qilingan mijoz `Saqlash`ni bossa, mahsulot darhol saqlanadi.
6. Mijoz saqlanganlar sahifasida mahsulotlarni o‘qiydi va har birini o‘chirishi mumkin.

## 6. Navigatsiya qoidalari

- Bosh sahifa (`/`) allaqachon kategoriyalar ro‘yxati. Unda o‘z-o‘ziga qaytaradigan Back tugmasi bo‘lmaydi; brauzer Back oldingi tarix yozuviga qaytadi. Sayt brauzer tabini majburan yopa olmaydi.
- Mahsulotlar sahifasidagi sayt Back tugmasi kategoriyalar sahifasiga olib boradi.
- Product detail sahifasidagi sayt Back tugmasi mahsulot qaysi kategoriyaga tegishli bo‘lsa, o‘sha kategoriya mahsulotlari sahifasiga qaytaradi. Product API shu maqsad uchun `category.slug` qaytaradi.
- Brauzerning Back tugmasi tabiiy history bo‘yicha ishlaydi; sayt tugmalari esa aniq parent URLga yo‘naltiradi. To‘g‘ridan-to‘g‘ri product URL ochilganda ham sayt Back uning kategoriyasiga qayta oladi.

## 7. Product ma’lumotlari

Product detail: name, image, price, availability, short description va do‘kon tasdiqlagan `detailed_information`.

`detailed_information` — mahsulot qutisidagi yo‘riqnoma yoki tegishli rasmiy hujjatdagi mavjud ma’lumotlar. Bu ma’lumotni do‘kon mas’ul shaxsi tekshiradi. Tizim tashxis qo‘ymaydi va individual davolash tavsiyasi bermaydi.

## 8. Asosiy biznes qoidalari

- Katalogni ko‘rish uchun akkaunt kerak emas.
- Faqat authenticated user Favorites bilan ishlaydi.
- Foydalanuvchi faqat o‘z SavedProduct yozuvlarini ko‘radi va o‘chiradi.
- Bitta user bir mahsulotni takroran saqlay olmaydi.
- SavedProduct mahsulot ma’lumotini nusxalamaydi; Product ma’lumotlari yangilansa, Favorites ham yangilangan ma’lumotni ko‘rsatadi.
- `is_available=False` mahsulot butunlay o‘chirildi degani emas; bunday mahsulotni ham favoritesga saqlash mumkin.
- Product butunlay o‘chirilsa, tegishli SavedProduct bog‘lanishlari o‘chadi.
- Mahsulotga bog‘langan Category'ni Category o‘chirib tashlash orqali tasodifan yo‘qotib bo‘lmaydi; avval mahsulotlarni ko‘chirish yoki o‘chirish kerak.

## 9. Scope — MVP ichida

- Kategoriyalar ro‘yxati
- Kategoriyadagi mahsulotlar
- Product detail
- Product mavjudlik holati
- Registration/login/JWT
- Favorites: save/list/delete
- Django Admin orqali Category/Product CRUD
- DRF va OpenAPI/Swagger
- PostgreSQL, Docker/Compose, Nginx, HTTPS, AWS EC2
- Asosiy avtomatik testlar

## 10. Scope tashqarisida

- Mahsulot qidiruvi (keyingi feature bo‘lishi mumkin, lekin tasdiqlangan MVPda yo‘q)
- Cart, order, checkout, payment, delivery, courier, address/GPS
- Telegram bot, SMS OTP, e-mail reset
- Reviews/comments, notifications, AI maslahat
- Branch management, boshqa davlatlar uchun valyuta va tillar
- Redis, Celery, RabbitMQ, microservices, Kubernetes, GraphQL, Elasticsearch

## 11. MVP muvaffaqiyat mezonlari

- Guest barcha public katalog sahifalarini ko‘ra oladi.
- Admin mahsulot va kategoriya ma’lumotini Django Admin orqali o‘zgartira oladi.
- O‘zgarishlar keyingi API javoblari va sahifa yuklanishlarida aks etadi.
- Registrationdan keyin pending save muvaffaqiyatli amalga oshadi.
- Mijoz faqat o‘z Favorites ma’lumotini ko‘ra/o‘chira oladi.
- Docker orqali ishga tushadi va AWS EC2'da HTTPS bilan tekshirilgan.
- Asosiy testlar o‘tadi, backup/restore yo‘riqnomasi mavjud.
