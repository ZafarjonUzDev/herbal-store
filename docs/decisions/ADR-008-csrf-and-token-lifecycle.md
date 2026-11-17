# ADR-008: Cookie refresh, CSRF va multi-page autentifikatsiya

- **Status:** Accepted for MVP v1.1
- **Decision date:** 2026-10-12

## Context

Refresh cookie HttpOnly, access JWT JS memoryda. Multi-page navigation memoryni tozalaydi. DRF APIView'da CSRF himoyasini token requestlariga alohida kafolatlash va logout/refresh semantikasini to‘g‘ri belgilash kerak.

## Decision

- `GET /api/v1/auth/csrf/` CSRF cookie va JSON token beradi.
- `POST /api/v1/auth/register/`, `/token/`, `/token/refresh/`, `/logout/` explicit `csrf_protect` yoki ekvivalent himoya va Origin siyosati bilan ishlaydi. `enforce_csrf_checks=True` testlar yoziladi.
- Simple JWT rotation/blacklist ishlatiladi; refresh JWT JSON bodyga chiqmaydi, faqat HttpOnly cookie.
- `Saqlash` clickidan va Favorites load'dan oldin silent refresh sinab ko‘riladi; bir tabda concurrent refresh single-flight bo‘ladi.
- Login va registration ikkalasi ham pending save ID'ni avtomatik saqlash bilan yakunlaydi.
- Logout refresh tokenni bekor qiladi; access JWTni browser memorydan o‘chiradi. Stolen access token expiry'gacha ishlashi mumkin, shuning uchun access umr qisqa.

## Consequences

- Oddiy JSON JWT flowga qaraganda custom auth view va integration test ko‘proq kerak.
- Mijoz sahifalar orasida yurganda o‘zini yana guest deb ko‘rmaydi.
- Cookie security/CSRF server va browserda bir xil test qilinishi shart.

## Phase 1–3 tekshiruv izohi — 2026-10-13

Auth view'laridagi `authentication_classes=()` saqlanadi. DRF noto‘g‘ri login yoki refresh cookie yo‘qligidagi `AuthenticationFailed`ni `403`ga aylantirmasligi uchun `get_authenticate_header()` Bearer challenge qaytaradi; mavjud API kontraktidagi `401` tiklanadi. SimpleJWT user lookup'ida o‘chirilgan user ham refresh rad etilishiga kiradi: umumiy `401` va cookie tozalash. CSRF/Origin uchun `403`, refresh rotation, blacklist va token saqlash qarorlari saqlanadi. PostgreSQL integration tekshiruvining joriy holati `docs/implementation/PHASE-1-3-RUNTIME-REPORT.md`da qayd etiladi.


## Lokal MVP frontend lifecycle aniqlashtirishi — 2026-10-13

Frontend access tokenni ES modul xotirasida saqlaydi; public navigatsiya refresh talab qilmaydi. Save va Favorites silent refresh bilan tekshiriladi; API 401 bo‘lsa bir martalik refresh/retry bajariladi. CSRF/Origin 403 yoki network xatosi guest deb talqin qilinmaydi. Login/register ikkalasi pending Save’ni alohida API bilan yakunlaydi; auth Bekor/Back va boshqa sahifaga joriy-tab havolasi intentni tozalaydi; auth reload, login↔register almashtirish va formvalidation uni saqlaydi. Public sahifa init/pageshow browser Back orqali qaytilganda ham intentni tozalaydi.

Logout mavjud single-flight refresh javobini kutadi va shu vaqt yangi refresh boshlanishini bloklaydi; keyin cookie blacklist/tozalash POSTini bajaradi va memory accessni o‘chiradi. Bu rotation javobi logoutdan keyin refresh cookie’ni qayta o‘rnatishini oldini oladi. 16 ta browser regression tekshiruvi lifecycle, storage chegaralari va ushbu poyga tartibini tasdiqladi.

Login ham registratsiya kabi username’ni field validatsiyasidan oldin NFKC normalizatsiya qiladi; whitespace native tarzda olib tashlanadi, case-sensitive xulq saqlanadi. Unicode username bilan register/logout/login regressiyasi PostgreSQLda o‘tdi.

## UI/UX holatini tiklash — 2026-11-01

Saqlangan bookmark holatini dastlabdan to‘g‘ri ko‘rsatish uchun category/detail sahifalari renderdan keyin silent refresh va user-scoped Favorites GET bajaradi. Shu tariqa yuqoridagi “public navigatsiya refresh talab qilmaydi” iborasi ushbu ikki sahifadagi holat ko‘rsatish uchun aniqlashtirildi. Katalogning public GET kontrakti va anonim kirish huquqi o‘zgarmaydi; auth yoki favorites tekshiruvi xatosi public ma’lumotni yashirmaydi. Home sahifasi refresh talab qilmaydi.

Browser bfcache orqali qaytilganda `resetAuthentication()` document xotirasidagi eski accessni tashlaydi, auth versiyasini yangilaydi va eski refreshni kutadi. Keyingi loader cookie orqali joriy sessiyani tiklaydi; boshqa sahifada logout/login qilingan akkauntning avvalgi accessi ishlatilmaydi. Save o‘rniga Remove bosilgan paytdagi 401 yangi pending Save yaratmaydi; login → Favorites orqali davom etadi. CSRF/Origin, cookie atributlari, token muddati, rotation/blacklist va web storage chegaralari o‘zgartirilmagan.
