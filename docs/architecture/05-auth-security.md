# 05 — Authentication & Security Architecture (reviewed v1.1)

## 1. Ikki auth yo‘li

- Customer API: JWT access token.
- Django Admin: Django session authentication va staff/superuser permissionlari.

Customer JWT'si Django Admin loginini bermaydi. Oddiy registration `is_staff` yoki `is_superuser` huquqini bera olmaydi.

## 2. User modeli

Loyiha boshida `accounts.User(AbstractUser)` yaratiladi va `AUTH_USER_MODEL = "accounts.User"` belgilanadi. Public registration faqat `username` va `password` yig‘adi. Username Django defaultga mos holda katta-kichik harfga sezgir; ism/familiya, email yoki telefon talab qilinmaydi. Password Django password hasherlari bilan saqlanadi.

Registration va login username'ni Django `create_user()` kabi NFKC normalizatsiya qiladi; bu uniqueness, uzunlik va belgilar validatsiyasidan **oldin** bajariladi. DRF chetdagi whitespace'ni olib tashlaydi; saqlangan username chetida bo‘sh joy bo‘lmaydi. Normalizatsiya case-folding qilmaydi: `Ali` va `ali` alohida username bo‘lib qoladi.

## 3. Token saqlash strategiyasi

- Access JWT: JavaScript modul xotirasida; `localStorage`/`sessionStorage`ga saqlanmaydi.
- Refresh JWT: HttpOnly cookie; JS uni o‘qiy olmaydi.
- Refresh token rotation va blacklist yoqiladi, token blacklist app loyiha konfiguratsiyasiga kiritiladi. Browser endpointlari Simple JWT default JSON refresh viewini **to‘g‘ridan-to‘g‘ri ishlatmaydi**: cookie input/output uchun aniq moslashtirilgan view bo‘ladi; yangi refresh JWT javob bodyga chiqmaydi.
- Access token tavsiya etilgan boshlang‘ich umr: 15 daqiqa; refresh token: 7 kun. Bular konfiguratsiya, implementatsiyadan keyin xavfsizlik va UX sinoviga qarab tekshiriladi.

Cookie:
- Production: `__Secure-refresh` nomi, `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/api/v1/auth/`, `Domain` belgilanmaydi.
- Development HTTP localhost: secure prefix ishlatmaydigan alohida `refresh_token` nomi va `Secure=False` faqat lokal konfiguratsiyada.
- Productionda `Secure=False` bo‘lishiga yo‘l qo‘yilmaydi.

`__Secure-` prefiksi Secure atributi talab qiladi. Cookie path'ini auth endpointlari bilan cheklash refresh tokenning boshqa API requestlarida yuborilishini kamaytiradi.

## 4. Multi-page frontenddagi access token

Har bir full-page navigation yangi JS execution context yaratadi, demak memorydagi access token yo‘qoladi. Har bir protected page ishga tushganda frontend:

1. CSRF tokenini oladi (`GET /api/v1/auth/csrf/`).
2. Refresh cookie mavjud bo‘lsa refresh endpointini chaqiradi.
3. Yangi access tokenni memoryga qo‘yadi.
4. Shundan keyin Favorites API'ga murojaat qiladi.

**Muhim:** kategoriya/product sahifasidagi `Saqlash` tugmasida ham avval silent refresh bilan session bor-yo‘qligi tekshiriladi. Yangi HTML sahifaga o‘tgani uchun memory token yo‘qolganini `Guest` deb noto‘g‘ri qabul qilmaslik kerak. Bir tabdagi parallel refresh so‘rovlari bitta umumiy Promise orqali navbatga qo‘yiladi, chunki rotation bir refresh tokenni qayta ishlatishni rad qilishi mumkin.

Public catalog uchun bu refresh jarayoni shart emas; uni faqat authenticated sahifa/operation talab qilganda ishga tushirish mumkin.

## 5. CSRF va Origin

Refresh token cookie'da bo‘lgani uchun refresh/logout va refresh cookie o‘rnatadigan login/register flow'larida CSRF/Origin himoyasi amalga oshiriladi.

- `/api/v1/auth/csrf/` CSRF tokenini JSON orqali beradi va CSRF cookie o‘rnatilishini kafolatlaydi.
- DRF APIView'larida sessionga bog‘liq CSRF tekshiruviga suyanmaymiz. `register`, `token`, `token/refresh`, `logout` POST’lari `csrf_protect` (yoki security jihatdan ekvivalent mexanizm) bilan aniq himoyalanadi. Testlarda DRF test client CSRF tekshiruvlari **haqiqatan yoqilgan** bo‘ladi.
- Frontend `X-CSRFToken` yuboradi.
- Backend mos Origin/Host siyosatini tekshiradi.
- `SameSite=Strict` qo‘shimcha himoya, ammo yagona CSRF himoyasi emas.
- Protected Favorites POST/DELETE requestlari access tokenni `Authorization: Bearer ...` headerida yuboradi va refresh cookie'dan autentifikatsiya qilinmaydi.
- Logoutdagi blacklist refresh credentialini bekor qiladi, **oldin berilgan access JWTni emas**. JS access state tozalanadi, lekin qo‘lga tushgan access token muddati tugaguncha kuchda bo‘lishi mumkin. Shu sababli access JWT qisqa umrli.

Noto‘g‘ri login va refresh cookie yo‘qligi API kontrakti bo‘yicha `401`; DRF shu statusni saqlashi uchun auth view `WWW-Authenticate: Bearer realm="api"` challenge beradi. Bu auth endpointlariga Bearer token talabini qo‘shmaydi. Refresh tokenning user'i o‘chirilgan yoki inactive bo‘lsa, backend umumiy `401` qaytaradi va refresh cookie'ni tozalaydi; CSRF/Origin rad etilishi esa `403` bo‘lib qoladi.

## 6. Registration va saqlash intenti

Mijoz Guest holatida `Saqlash`ni bossa, product ID tab/session doirasidagi `sessionStorage`ga `pendingSaveProductId` sifatida vaqtincha yoziladi. Bu parol yoki token emas.

1. User registrationga yuboriladi.
2. Registration muvaffaqiyatli bo‘lib JWT state o‘rnatiladi.
3. Frontend pending ID'ni o‘qib Favorites POST so‘rovini yuboradi. Bu flow eski akkauntiga **login** qilgan user uchun ham aynan shunday ishlaydi.
4. Saqlash muvaffaqiyatli bo‘lsa pending state tozalanadi va Favorites sahifasi ochiladi.
5. Registration/login validation xato bo‘lsa pending state saqlanadi (qayta urinishi uchun); foydalanuvchi **Orqaga/Bekor** tugmasini bosib jarayondan chiqsa pending state tozalanadi. Tab yopilsa ham sessionStorage yo‘qoladi.
6. Backend yuborilgan product ID'ni qayta tekshiradi. `sessionStorage`dagi qiymatga ishonmaydi.

Registration endpoint Favorite yaratmaydi; accounts va favorites modullari ajratilgan qoladi.

## 7. Authorization qoidalari

| Aktor | Ruxsat |
|---|---|
| Guest | Category/Product public GET |
| Authenticated customer | Public GET + o‘z Favorites list/create/delete |
| Customer | Category/Product create/update/delete yo‘q |
| Staff/superuser | Django Admin permissionlari doirasida boshqarish |

Favorites querysetlari doimo `request.user` bilan cheklanadi. DELETE lookup ham `user=request.user` shartini o‘z ichiga oladi.

## 8. Abuse prevention

- Registration/login endpointlariga throttle/rate limit. DRF cache throttle bir nechta workerda kafolatli global limit emas; productionda Nginx `limit_req` kabi tashqi qatlamdagi rate limit ham ko‘riladi.
- Username unikal va tekshiriladi; whitespace chetida bo‘lmasligi kerak. v1.1 **case-sensitive**; `Ali` va `ali` bitta akkaunt deb taxmin qilinmaydi.
- Password validation Django validators orqali.
- Bir xil user-product bookmark duplicate'i DB unique constraint bilan bloklanadi.
- Upload faqat admin uchun; image format va hajm serverda tekshiriladi.
- Maxfiy credential/token/cookie qiymatlari log qilinmaydi.
- Admin kuchli password bilan himoyalanadi; staff huquqi public registrationdan berilmaydi.

DRF throttle oddiy application-level rate limiting; u to‘liq DDoS yoki brute-force platformasi o‘rnini bosmaydi. Zarurat tug‘ilsa proxy/WAF qatlamida qo‘shimcha himoya ko‘rib chiqiladi.

## 9. Django production security

Productionda:
- `DEBUG=False`;
- to‘g‘ri `ALLOWED_HOSTS` va `CSRF_TRUSTED_ORIGINS`;
- secretlar environment/secret manbasidan;
- `SECURE_SSL_REDIRECT` yoki Nginx redirect, proxy HTTPS sozlamalari bir-biriga mos;
- `SECURE_PROXY_SSL_HEADER` faqat Nginxdan keladigan ishonchli forwarded header bilan sozlanadi;
- HTTPS va mos HSTS siyosati sertifikat/HTTPS tekshirilgach yoqiladi;
- DB va Gunicorn portlari tashqi tarmoqqa publish qilinmaydi.

## 10. Mahsulot kontenti va sog‘liq bilan bog‘liq ma’lumot

`detailed_information` oddiy matn sifatida chiqariladi; frontend user/admin kiritgan matnni raw HTML qilib bajarmaydi. Do‘kon mahsulot yo‘riqnomasi, ishlab chiqaruvchi ma’lumoti va boshqa sog‘liq bilan bog‘liq claims'larning manbasi/to‘g‘riligini tasdiqlashi kerak. Tizim individual diagnoz yoki davolash tavsiyasi bermaydi.
