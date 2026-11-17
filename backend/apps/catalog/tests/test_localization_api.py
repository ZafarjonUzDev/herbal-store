"""Tanlangan til katalog/favoritesning shaxsini yoki autentifikatsiyasini almashtirmaydi."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.catalog.models import Category, CategoryTranslation, Product, ProductTranslation
from apps.favorites.models import SavedProduct


class LocalizedCatalogAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Sinov guruhi', slug='stable-category')
        cls.product = Product.objects.create(
            category=cls.category, name='Sinov mahsuloti', slug='stable-product',
            image='products/unchanged.webp', price='12000.50', is_available=False,
            description='UZ sinov tavsifi.', detailed_information='UZ sinov tafsiloti.',
        )
        cls.user = get_user_model().objects.create_user(username='language_customer')
        cls.saved = SavedProduct.objects.create(user=cls.user, product=cls.product)

    def russian(self):
        CategoryTranslation.objects.create(category=self.category, language='ru', name='Тестовая группа')
        ProductTranslation.objects.create(
            product=self.product, language='ru', name='Тестовое название',
            description='Тестовое описание.', detailed_information='Тестовые сведения.',
        )

    def test_default_uz_contract_is_unchanged_and_accept_language_does_not_override_it(self):
        response = self.client.get('/api/v1/products/stable-product/', HTTP_ACCEPT_LANGUAGE='ru')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], self.product.name)
        self.assertNotIn('language', response.data)
        self.assertEqual(response['Content-Language'], 'uz')

    def test_explicit_uz_metadata_and_all_original_content(self):
        response = self.client.get('/api/v1/products/stable-product/?lang=uz')
        self.assertEqual(response.data['language'], 'uz')
        self.assertTrue(response.data['translation_available'])
        for field in ('name', 'description', 'detailed_information'):
            self.assertEqual(response.data[field], getattr(self.product, field))
        self.assertEqual(response.data['category']['name'], self.category.name)

    def test_ru_reads_only_manually_entered_translation_and_shared_fields_are_equal(self):
        self.russian()
        original = self.client.get('/api/v1/products/stable-product/').data
        response = self.client.get('/api/v1/products/stable-product/?lang=ru')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Language'], 'ru')
        self.assertEqual(response.data['name'], 'Тестовое название')
        self.assertEqual(response.data['description'], 'Тестовое описание.')
        self.assertEqual(response.data['detailed_information'], 'Тестовые сведения.')
        self.assertTrue(response.data['translation_available'])
        self.assertEqual(response.data['category']['name'], 'Тестовая группа')
        for field in ('id', 'slug', 'image', 'price', 'is_available'):
            self.assertEqual(response.data[field], original[field])
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Sinov mahsuloti')

    def test_missing_ru_is_explicit_null_without_uz_fallback(self):
        response = self.client.get('/api/v1/products/stable-product/?lang=ru')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['translation_available'])
        for field in ('name', 'description', 'detailed_information'):
            self.assertIsNone(response.data[field])
        self.assertIsNone(response.data['category']['name'])
        self.assertFalse(response.data['category']['translation_available'])
        self.assertEqual(response.data['slug'], self.product.slug)

    def test_category_and_product_translation_availability_are_independent(self):
        CategoryTranslation.objects.create(category=self.category, language='ru', name='Тестовая группа')
        response = self.client.get('/api/v1/categories/stable-category/products/?lang=ru')
        self.assertTrue(response.data['category']['translation_available'])
        self.assertFalse(response.data['products'][0]['translation_available'])

    def test_category_envelope_localizes_with_bounded_queries(self):
        self.russian()
        with self.assertNumQueries(4):
            response = self.client.get('/api/v1/categories/stable-category/products/?lang=ru')
        self.assertEqual(set(response.data), {'category', 'products'})
        self.assertEqual(response.data['category']['name'], 'Тестовая группа')
        self.assertEqual(response.data['products'][0]['name'], 'Тестовое название')
        self.assertIn('no-store', response['Cache-Control'])
        with self.assertNumQueries(2):
            categories = self.client.get('/api/v1/categories/?lang=ru')
        self.assertEqual(categories.data[0]['name'], 'Тестовая группа')

    def test_ru_favorites_use_same_relation_current_values_and_bounded_queries(self):
        self.russian()
        self.client.force_authenticate(self.user)
        with self.assertNumQueries(3):
            response = self.client.get('/api/v1/me/saved-products/?lang=ru')
        self.assertEqual(response.status_code, 200)
        item = response.data[0]
        self.assertEqual(item['name'], 'Тестовое название')
        self.assertEqual(item['category']['name'], 'Тестовая группа')
        self.assertEqual(item['id'], self.product.pk)
        self.assertEqual(item['price'], '12000.50')
        self.assertFalse(item['is_available'])
        again = self.client.post('/api/v1/me/saved-products/?lang=ru', {'product_id': self.product.pk}, format='json')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(SavedProduct.objects.get().pk, self.saved.pk)
        self.assertEqual(self.client.delete(f'/api/v1/me/saved-products/{self.product.pk}/?lang=ru').status_code, 204)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_missing_ru_favorite_remains_visible_with_shared_values(self):
        self.client.force_authenticate(self.user)
        item = self.client.get('/api/v1/me/saved-products/?lang=ru').data[0]
        self.assertIsNone(item['name'])
        self.assertFalse(item['translation_available'])
        self.assertEqual(item['id'], self.product.pk)

    def test_only_uz_and_ru_are_accepted(self):
        for language in ('en', 'RU', '', 'ru,uz'):
            with self.subTest(language=language):
                response = self.client.get('/api/v1/categories/', {'lang': language})
                self.assertEqual(response.status_code, 400)
                self.assertIn('lang', response.json())

    def test_ru_guest_still_cannot_read_or_write_favorites(self):
        self.assertEqual(self.client.get('/api/v1/me/saved-products/?lang=ru').status_code, 401)
        response = self.client.post('/api/v1/me/saved-products/?lang=ru', {'product_id': self.product.pk}, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(SavedProduct.objects.count(), 1)


class UzbekAdminLanguageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_superuser(username='locale_admin', password='test-locale-only')

    def test_login_and_common_admin_controls_are_uz_even_for_ru_browser(self):
        response = self.client.get('/admin/login/', HTTP_ACCEPT_LANGUAGE='ru')
        self.assertContains(response, 'Kirish')
        self.assertContains(response, 'Foydalanuvchi nomi')
        self.assertNotContains(response, 'Log in')
        self.client.force_login(self.staff)
        response = self.client.get('/admin/catalog/product/add/?lang=ru', HTTP_ACCEPT_LANGUAGE='ru')
        self.assertContains(response, 'Umumiy ma’lumotlar')
        self.assertContains(response, 'O‘zbekcha (UZ)')
        self.assertContains(response, 'Ruscha (RU)')
        self.assertContains(response, 'Saqlash va yana qo‘shish')
        self.assertNotContains(response, 'Save and add another')
        self.assertEqual(response['Content-Language'], 'uz')
