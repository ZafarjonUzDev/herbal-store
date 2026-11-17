# 07 — Backend Internal Architecture

## UZ/RU qo‘shimchasi — 2026-11-03

Catalog translation modellari va parent Admin formalari [ADR-010](../decisions/ADR-010-uz-ru-localization.md)
bo‘yicha ishlaydi. `catalog/localization.py` mavjud serializerlarga til tanlash va
RU prefetch yordamchilarini beradi; catalog favoritesga bog‘lanmaydi. Favorites
shu read serializerdan foydalanadi. `config.middleware.InterfaceLanguageMiddleware`
Adminni UZda, API’ni explicit `lang` yoki default UZda saqlaydi; auth himoyasi
o‘zgarmaydi. `backend/locale/uz` standart Django Admin/Auth/JS matnlarini
o‘zbekchalashtiradi. Standart Django Admin CRUD va uning transactioni saqlanadi.

## 1. Application style

Django + DRF modular monolith. Hozirgi biznes logikasi uchun odatiy Django models, serializers, generic API views va ORM yetarli.

## 2. Ilovalar

### `accounts`

Mas’uliyat:
- Custom `User` model.
- Registration serializer/view.
- JWT login/refresh/logout flow va cookie boshqaruvi.
- CSRF token endpoint.

### `catalog`

Mas’uliyat:
- `Category`, `Product` modellari.
- Category list, category products, product detail API.
- Admin panel orqali catalog CRUD.
- Product list/detail serializerlari.

### `favorites`

Mas’uliyat:
- `SavedProduct` modeli.
- Authenticated current user uchun list/create/delete API.
- Duplicate relationni boshqarish.
- `request.user` bilan queryset scope.

## 3. Tavsiya etilgan fayl chegaralari

Har bir appda Django startapp'ning kerakli fayllari:
- `models.py`
- `serializers.py`
- `views.py`
- `urls.py`
- `admin.py`
- `apps.py`
- `migrations/`
- `tests/`

Alohida `services.py`, `repositories.py`, `selectors.py`, `interfaces.py` yo‘q — hozircha biznes mantiqi bunday abstraksiyani oqlamaydi. Agar bir amalda bir nechta biznes operatsiya paydo bo‘lsa, keyin qayta ko‘riladi.

## 4. Views

- Category list: `ListAPIView` yoki unga teng read-only view, `AllowAny`.
- Category products: category slug bo‘yicha queryset; category yo‘q bo‘lsa 404; `AllowAny`; response `{"category": {...}, "products": [...]}` envelope bilan qaytadi.
- Product detail: product slug bo‘yicha read-only detail, `AllowAny`.
- Favorites list/create: bir view/classda `GET` va `POST` bo‘lishi mumkin, `IsAuthenticated`. Duplicate create 200 bilan qaytadi va poyga holati `500`ga chiqmasligi kerak; mavjud bo‘lmagan `product_id` 400 serializer field xatosi.
- Favorites delete: `DestroyAPIView` yoki aniq delete view, queryset current user bilan cheklangan.

`ModelViewSet` catalog uchun tanlanmaydi, chunki public API read-only va admin CRUD allaqachon Django Admin'da bor.

## 5. Serializers

- `CategoryListSerializer`: `id`, `name`, `slug`.
- `CategoryProductSerializer`: `id`, `name`, `slug`, `image`, `price`, `is_available`.
- `ProductDetailSerializer`: list fieldlari + `category {name, slug}`, `description`, `detailed_information`.
- `RegisterSerializer`: username/password validation va user creation.
- `SavedProductCreateSerializer`: faqat `product_id` qabul qiladi; user requestdan olinadi.
- `SavedProductReadSerializer` yoki equivalent projection: Productning amaldagi ma’lumotlari + `saved_at`.

## 6. Muhim validatsiya va token cheklovi

- `Product.price` uchun serializer/model validatorga qo‘shimcha ravishda PostgreSQL `CHECK(price >= 0)`.
- `Product.detailed_information` barcha e’lon qilingan mahsulotlar uchun majburiy bo‘ladi.
- Auth POST view'larida Django CSRF mexanizmini **ochiq qo‘llash** kerak; DRF APIView avtomatik CSRF deb hisoblanmaydi.
- Refresh rotationda yangi token faqat HttpOnly cookie'ga yoziladi, API JSONda faqat access qaytadi.
- Public JSON javoblari server cache'iga tayanmaydi (`Cache-Control: no-store`).

## 7. Database query efficiency

Favorites listda Product ma’lumoti ham qaytarilgani uchun N+1 query oldini olish maqsadida `select_related("product", "product__category")` ishlatiladi. Category products query faqat zarur fieldlarni qaytaradi; qo‘shimcha optimizatsiya o‘lchov yoki aniq query zaruratiga qarab qilinadi.

## 8. Admin

- `CategoryAdmin`: list display, search, slug prepopulation.
- `ProductAdmin`: product name, category, price, availability, updated date listda; search, category/availability filterlar; slug prepopulation; category relation uchun zarur bo‘lsa `list_select_related`.
- Public API product/category yozmaydi.
- SavedProduct uchun maxsus admin CRUD shart emas; kerak bo‘lsa faqat readonly ko‘rish qo‘shilishi mumkin.

## 9. API documentation

OpenAPI/Swagger `drf-spectacular` kabi mos paket orqali ishlab chiqiladi. Schema implementation qilingan endpointlarga mos bo‘lishi va request/response serializerlarini hujjatlashtirishi kerak.

## 10. Default exception/validation

DRF serializer validation request data'ni tekshiradi. DB constraints uniqueness/integrityni himoya qiladi. Error formatlar imkon qadar bir xil va xavfsiz bo‘ladi. Productionda DEBUG traceback response bermaydi.
