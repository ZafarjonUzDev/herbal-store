# 03 — Domain Model & Database Design

## UZ/RU qo‘shimcha qarori — 2026-11-03

[ADR-010](../decisions/ADR-010-uz-ru-localization.md) bo‘yicha CategoryTranslation
va ProductTranslation qo‘shildi: har bir obyekt/til uchun UNIQUE, `uz|ru` va
majburiy matn CHECKlari. Eski UZ ustunlari, ID/slug, rasmlar va Favorites aloqalari
saqlanadi; data migration faqat aynan eski UZ matnini ko‘chiradi. RU administrator
tomonidan qo‘lda kiritiladi; yetishmagan RU alohida holat. Quyidagi dastlabki
to‘rtta asosiy entity saqlanadi; translationlar shu katalog obyektlarining matnlari.

## 1. Entity'lar

MVP domenida 4 ta asosiy entity mavjud:

1. `User` — Django authentication foydalanuvchisi.
2. `Category` — mahsulotlar guruhi.
3. `Product` — do‘kon katalogidagi mahsulot.
4. `SavedProduct` — user va product orasidagi bookmark relation.

Django auth va admin o‘zining framework jadvallarini yaratadi; “4 entity” asosiy domen entitylarini anglatadi, PostgreSQLda jami aynan 4 ta jadval bo‘ladi degani emas.

## 2. ERD

```text
Category (1) ───────< Product (1) ───────< SavedProduct >────── (1) User
```

Aniq kardinalnost:
- Category 1:N Product. Har bir Product bitta Category'ga tegishli.
- User 1:N SavedProduct.
- Product 1:N SavedProduct.
- User va Product orasidagi mantiqiy munosabat SavedProduct orqali M:N, unique pair bilan cheklangan.

## 3. User

Django `AbstractUser` asosida custom user modeli loyiha boshida yaratiladi va `AUTH_USER_MODEL = "accounts.User"` sozlanadi.

Public registration faqat `username` va `password` talab qiladi. v1.1 da username **katta-kichik harfga sezgir**: `Ali` va `ali` Django default qoidalariga ko‘ra ikki xil username bo‘lishi mumkin. Frontend va backend buni bir xil talqin qiladi, username chetidagi bo‘sh joyni tekshiradi. Django `AbstractUser`ning framework uchun kerakli qo‘shimcha maydonlari va permission maydonlari qolishi mumkin, lekin frontend/API ularni ro‘yxatdan o‘tishda yig‘maydi. Parolni qo‘lda hash qilish yoki modelga plaintext saqlash taqiqlanadi; Django `create_user`/mos manager ishlatiladi.

User ID primary key bo‘ladi. Django `date_joined` yaratish vaqtini saqlaydi; alohida `created_at` majburiy emas.

## 4. Category

| Field | Tavsiya | Qoidalar |
|---|---|---|
| `id` | BigAutoField | PK |
| `name` | CharField | Required, unique |
| `slug` | SlugField | Required, unique, public URL uchun |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |

`is_active`, category image yoki category description biznes talabi bilan tasdiqlanmagan, shuning uchun MVPda yo‘q. Category endpointi mavjud barcha kategoriyalarni, mahsuloti yo‘q bo‘lsa ham, qaytaradi; bunday category uchun mahsulotlar ro‘yxati bo‘sh bo‘ladi.

## 5. Product

| Field | Tavsiya | Qoidalar |
|---|---|---|
| `id` | BigAutoField | PK |
| `category` | ForeignKey(Category) | Required, `on_delete=PROTECT`, related_name=`products` |
| `name` | CharField | Required; globally unique emas |
| `slug` | SlugField | Required, unique; detail URL identifier |
| `image` | ImageField | Required; `upload_to="products/"` |
| `price` | DecimalField(12, 2) | Required, `MinValueValidator(0)` **va DB `CheckConstraint(price__gte=0)`** |
| `is_available` | BooleanField | Default `True`; faqat sotuvdagi holatni ifodalaydi |
| `description` | TextField | Qisqa tavsif, MVPda required |
| `detailed_information` | TextField | Required; mahsulot qutisi yo‘riqnomasi yoki do‘kon tasdiqlagan batafsil axborot, oddiy matn |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |

### Narx

Pul `float` emas, `DecimalField`da saqlanadi. `MinValueValidator(0)` serializer/admin validatsiyasiga yordam beradi; `CheckConstraint(condition=Q(price__gte=0), name="product_price_nonnegative")` bevosita DB yozuvini ham himoya qiladi. Currency hozircha UZS deb qabul qilinadi va frontendda `so‘m` ko‘rsatiladi; currency fieldi qo‘shilmaydi.

### Slug

Slug mahsulotning public identifieridir. Yaratishda nomdan oldindan to‘ldirilishi mumkin. Mahsulot nomi o‘zgarganda slugni avtomatik qayta yozib, eski URLni buzmaslik kerak. Slug o‘zgarishini admin ongli ravishda bajarishi lozim.

### Mavjudlik

`True` → “Sotuvda”; `False` → “Hozircha sotuvda emas”. Bu Productni deaktivatsiya qilish yoki DBdan o‘chirish bilan teng emas.

### Batafsil ma’lumot

Heterogen qadoq/yo‘riqnoma matni uchun bitta **majburiy** `TextField` ishlatiladi. Yo‘riqnoma mavjud bo‘lmasa, admin do‘kon tasdiqlagan batafsil izohni kiritadi. MVPda `composition`, `dosage`, `warnings`, `storage` kabi barcha mahsulotga bir xil tushmaydigan 10+ ustun yaratilmaydi. Matn oddiy text sifatida ko‘rsatiladi, raw HTML sifatida emas. Do‘kon ma’lumotning to‘g‘riligini tasdiqlaydi.

## 6. SavedProduct

| Field | Tavsiya | Qoidalar |
|---|---|---|
| `id` | BigAutoField | PK |
| `user` | ForeignKey(settings.AUTH_USER_MODEL) | Required, `CASCADE`, related_name=`saved_products` |
| `product` | ForeignKey(Product) | Required, `CASCADE`, related_name=`saved_by_users` |
| `created_at` | DateTimeField | auto_now_add |

Modelda `UniqueConstraint(fields=["user", "product"], name="uniq_saved_product_per_user")` bo‘ladi.

SavedProduct Productning nomi, narxi yoki rasmi nusxasini saqlamaydi. Favorites API joriy Product ma’lumotini join orqali qaytaradi.

## 7. Delete rules

- Category → Product: `PROTECT`; mahsulotli categoryni o‘chirish taqiqlanadi.
- Product → SavedProduct: `CASCADE`; Product butunlay o‘chirilsa bookmark relationshiplari o‘chadi.
- User → SavedProduct: `CASCADE`; user o‘chirilsa bookmarklari o‘chadi.
- Product `is_available=False` bo‘lsa, SavedProduct saqlanib qoladi.

## 8. Tartiblash va query siyosati

- Category list: `name`, keyin `id` bo‘yicha tartiblanadi.
- Category products: `name`, keyin `id` bo‘yicha tartiblanadi.
- Favorites: `-created_at`, keyin `-id` bo‘yicha tartiblanadi.
- v1.1 da ro‘yxatlar paginationsiz qaytadi; katalog kattalashsa kontrakt alohida qayta ko‘riladi.

## 9. Index va constraint strategiyasi

- Unique slug va username constraintlari indeks ham yaratadi.
- `Product.category_id` ForeignKey indexiga tayaniladi.
- SavedProduct `(user_id, product_id)` unique constrainti duplicate'larni DB darajasida to‘xtatadi.
- Keraksiz index qo‘shilmaydi. Mahsulot nomi qidiruvi MVP scope'ida yo‘q.

## 10. Migration talabi

Custom User modeli birinchi migrationdan oldin yaratilishi shart. Schema o‘zgarishlari Django migrations bilan boshqariladi; productionda migratsiyadan oldin backup va release rejasiga amal qilinadi.
