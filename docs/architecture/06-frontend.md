# 06 — Frontend Architecture

## UZ/RU lokalizatsiyasi — 2026-11-03

`js/i18n.js` faqat qo‘lda yozilgan interfeys matnlarini boshqaradi. Standart UZ;
header UZ/RU tanlagichi `herbalStore.language`ni saqlab, joriy URLni reload qiladi.
`api.js` Catalog/Favorites GETga `?lang=uz|ru` qo‘shadi. DBdan kelgan matnlar
lug‘at bilan tarjima qilinmaydi. RU `translation_available=false` holatida aniq
yetishmagan tarjima xabari chiqadi; umumiy rasm/narx/ID/Save ishlayveradi.
JWT storage, silent refresh va pending Save avvalgi chegaralarda qoladi.
Browser Back/boshqa tabdagi til o‘zgarishi eski tilni qayta ko‘rsatmasligi
uchun `pageshow`/`storage` tekshiruvi bor. [ADR-010](../decisions/ADR-010-uz-ru-localization.md).

## 1. Texnologiyalar

- HTML5
- CSS3 (Flexbox, Grid, media queries)
- Vanilla JavaScript ES modules (`type="module"`)

React/Vue/Angular, Node.js frontend serveri va SPA router MVP uchun kerak emas. Frontend fayllari Nginx tomonidan beriladi va DRF API bilan same-origin orqali ishlaydi.

## 2. Sahifalar

| Fayl | Vazifa |
|---|---|
| `index.html` | Kategoriyalar ro‘yxati |
| `category.html?slug=...` | Tanlangan kategoriya mahsulotlari |
| `product.html?slug=...` | Bitta mahsulot detail |
| `favorites.html` | Authenticated userning saqlanganlari |
| `login.html` | Login formasi |
| `register.html` | Username/password registration |

## 3. JS modullari

- `js/api.js`: HTTP so‘rovlari, JSON/error handling va endpoint funksiyalari.
- `js/auth.js`: access token memory, CSRF token, refresh, login state va logout.
- `js/navigation.js`: sahifa URL/state va Back tugmasi yordamlari.
- `js/components/navbar.js`: umumiy header/navigation.
- `js/components/category-card.js`: kategoriya kartasi.
- `js/components/product-card.js`: mahsulot kartasi.
- `js/components/favorite-button.js`: Save action.
- `js/pages/home.js`, `category.js`, `product.js`, `favorites.js`, `login.js`, `register.js`: sahifalarning UI mantiqi.
- `js/utils/format-price.js`: UZS narx formatlash.
- `js/utils/notifications.js`: error/success xabarlari.

Bular boshlang‘ich logical boundaries; implementatsiya vaqtida keraksiz mayda fayllar yaratilmaydi. JS fayllar import qilinsa `type="module"` bilan yuklanadi.

## 4. Data flow

```text
Page module → api.js → fetch( same-origin /api/v1/... ) → DRF → response → page/component render
```

Sahifa fayllari raw `fetch` va JWT header yig‘ishni ko‘p joyda takrorlamaydi. Authenticated request central API client orqali yuboriladi.

## 5. Katalog sahifalari

- `index.html`: `GET /api/v1/categories/`.
- `category.html?slug={category_slug}`: `GET /api/v1/categories/{slug}/products/`.
- `product.html?slug={product_slug}`: `GET /api/v1/products/{slug}/`.
- Product detail response'dagi `category.slug` sayt Back tugmasini category products sahifasiga qaytarish uchun kerak.
- Browser Back natural history bo‘yicha ishlaydi; saytdagi Back tugmasi esa aniq parent route'ga olib boradi.

## 6. Favorites va auth flow

- Favorites sahifasi protected API chaqirishdan oldin auth initialization/refresh bajaradi.
- Productda Save bosilganda oldin **silent refresh** orqali real authenticated holat tekshiriladi: HTML page almashishi sabab yo‘qolgan access tokenni guest holati bilan adashtirmaymiz. Haqiqiy guest bo‘lsa product ID `sessionStorage`ga yozilib `register.html` ochiladi; mavjud akkauntli mijoz `login.html`ga o‘tishi mumkin.
- Registration **yoki login** muvaffaqiyatli bo‘lgach tegishli page module pending productni o‘qib `POST /api/v1/me/saved-products/` chaqiradi.
- Save muvaffaqiyatli bo‘lgach pending state tozalanadi va `favorites.html` ochiladi. User auth jarayonini **bekor qilsa**, pending state ham tozalanadi; invalid form xatosida qayta urinish uchun qoladi.
- Authenticated user Save bosganda shu POST bevosita yuboriladi.
- Favorites kartasidagi Remove `DELETE /api/v1/me/saved-products/{product_id}/` chaqiradi.

`sessionStorage` credential/token saqlash uchun emas; u faqat vaqtinchalik product ID intentini saqlaydi.

## 7. UI holatlari

Barcha API-driven sahifalar:
- Loading;
- Success/data;
- Empty state;
- Validation/API error;
- Network failure;
- Auth expired/session unavailable
holatlarini boshqaradi.

Mavjud bo‘lmagan mahsulot “topilmadi”dan farq qiladi: mavjud product `is_available=false` bilan ko‘rsatiladi.

## 8. Component semantics va accessibility

- Navigation uchun `<a>`, action uchun `<button>`.
- Form fieldlarida label.
- Rasmlarda tavsiflovchi `alt`.
- Keyboard bilan foydalanish va yetarli contrast.
- Responsive desktop/tablet/mobile layout.
- API'dan kelgan text raw HTML sifatida inject qilinmaydi; `textContent` yoki xavfsiz text rendering ishlatiladi.

## 9. Mahsulot ro‘yxati javobi va yangilanish

`GET /api/v1/categories/{slug}/products/` quyidagi ko‘rinishda keladi: `{"category": {"id": ..., "name": ..., "slug": ...}, "products": [...]}`. `category.js` sarlavha uchun `category.name`dan, kartalar uchun `products`dan foydalanadi.

Frontend qayta kirish/reload paytida API yangidan chaqiriladi. Admin o‘zgarishi **keyingi request**da ko‘rinadi; brauzerga real-time xabar yuborish scope'da yo‘q.

## 10. Browser history

Bosh sahifa `index.html` — kategoriyalar ro‘yxati, shuning uchun uning ichida **o‘ziga qaytaruvchi Back tugmasi yo‘q**. Brauzer Back tabiiy history bo‘yicha tashqi oldingi sahifaga qaytishi mumkin; yangi tabda sayt kod bilan tabni yopmaydi. `category.html`dagi site Back indexga olib boradi; `product.html`dagi site Back productning `category.slug` qiymatidan category sahifasini ochadi. Browser Back esa tabiiy browser history bilan ishlaydi. Bu ikki xil nazorat ataylab ajratiladi.

## Lokal MVP lifecycle tekshiruvi — 2026-10-13

Auth sahifasining reloadi va login↔register o‘tish pending intentni saqlaydi; Bekor, public Back va boshqa sahifaga joriy-tab havolasi uni tozalaydi. Login/register uchun formning HTML fallbacki ham POST: parol URLga yozilmaydi. Logout davom etayotgan refreshni kutadi, keyin cookie’ni tozalaydi. 16 ta browser regression hamda haqiqiy Chrome asosiy oqimlari tasdiqlangan; [lokal hisobot](../implementation/MVP-LOCAL-REPORT.md).

## UI/UX refinement — 2026-11-01

- `js/config.js`dagi `siteConfig` frontend nom va logo manzilining yagona manbasi. Barcha sahifalar JS orqali umumiy nomni ishlatadi; same-origin logo yuklanmasa mavjud SVG fallback qoladi. Yangi model/API yo‘q.
- Category/detail yuklangach silent refresh va Favorites GET mahsulotlarning saqlangan holatini aniqlaydi. Holat tekshirilguncha tugmalar band; network/403 xatosida holat noma’lum qolib, **Qayta tekshirish** GETni takrorlaydi. Public katalog xatodan qat’i nazar ko‘rinadi.
- Bookmark konturli **Saqlash** → POST; yashil to‘liq bookmark **Saqlangan** → DELETE. Holat faqat muvaffaqiyatli javobdan keyin o‘zgaradi; DELETE 404 relation allaqachon yo‘qligini bildiradi. Boshqa xatolar oxirgi tasdiqlangan holatni saqlaydi. Favorites sahifasidagi **O‘chirish** alohida saqlanadi.
- Saqlashda guest auth oqimi avvalgidek pending Save yaratadi. O‘chirishda sessiya tugashi yangi Save intentini yaratmaydi: user login orqali Favoritesga qaytadi.
- `pageshow.persisted` public/protected sahifani qayta yuklaydi; oldin eski document accessi tashlanib, mavjud refresh tugashi kutiladi. Keyingi auth tekshiruvi joriy cookie orqali bajariladi.
- Kategoriya va Favorites bir xil ixcham vertikal kartadan foydalanadi: rasm → nom → mavjudlik → narx → **Batafsil** → Save/Remove; tavsif va yo‘riqnoma detail sahifasida qoladi. Grid: 700px dan kichikda 2, 700px dan 3, 1000px dan 4, 1400px dan 5 ustun. Rasmlar `object-fit: contain`; tugmalar ustma-ust, markazda, 12px radius va kamida 44px balandlikda. Desktopda tugma eni 60%, matn sig‘ishi uchun kamida 126px (karta enidan oshmaydi); kichik ekranda mavjud enni egallaydi.
- Saqlangan sana `Asia/Tashkent` vaqtida `Saqlangan: dd.mm.yyyy`; `<time datetime>` asl API vaqtini saqlaydi.
- Login/register ko‘zchasi `type=button`, `aria-controls` va `aria-pressed` bilan ishlaydi; backendning to‘rtta amaldagi password validatori yordam matnida aks etgan.
- **Chiqish** native `<dialog>` tasdiqlash oynasini ochadi. Dastlab fokus **Bekor qilish**da; Bekor/Escape sessiyani saqlaydi va fokusni Chiqish tugmasiga qaytaradi. **Ha, chiqish** mavjud `logout()`ni chaqiradi; so‘rov davomida takroriy amal bloklanadi. Xatoda oyna xavfsiz alert bilan ochiq qoladi va qayta urinish/bekor qilish mumkin. Cookie/CSRF/JWT lifecycle o‘zgarmaydi.

Yakuniy karta/logout tekshiruvi: Django **80/80**, frontend **34/34**, Chrome’da 280–1600px oralig‘ida katalog/Favorites uchun **14 responsive ssenariy PASS**. Tafsilotlar: [yakuniy UI hisoboti](../implementation/FINAL-PRODUCT-CARDS-REPORT.md).
