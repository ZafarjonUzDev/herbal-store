"""Django Admin orqali katalog CRUD ishlashi uchun integratsion testlar."""

from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from PIL import Image

from apps.catalog.admin import ProductAdminForm
from apps.catalog.models import Category, CategoryTranslation, Product, ProductTranslation


class CatalogAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username='storeadmin', password='SecureAdminPassword!123'
        )

    def setUp(self):
        self.client.force_login(self.admin_user)
        self.media_dir = TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()

    def tearDown(self):
        self.media_settings.disable()
        self.media_dir.cleanup()

    @staticmethod
    def sample_image():
        buffer = BytesIO()
        Image.new('RGB', (10, 10), (150, 200, 130)).save(buffer, format='PNG')
        return SimpleUploadedFile('moychechak.png', buffer.getvalue(), content_type='image/png')

    def test_models_registered_only_in_django_admin(self):
        self.assertTrue(admin.site.is_registered(Category))
        self.assertTrue(admin.site.is_registered(Product))

    def test_superuser_can_create_and_update_catalog_from_admin(self):
        category_response = self.client.post('/admin/catalog/category/add/', {
            'name': 'Giyohlar',
            'slug': 'giyohlar',
            '_save': 'Save',
        })
        self.assertEqual(category_response.status_code, 302)
        category = Category.objects.get(slug='giyohlar')

        create_response = self.client.post('/admin/catalog/product/add/', {
            'category': str(category.pk),
            'name': 'Moychechak',
            'slug': 'moychechak',
            'image': self.sample_image(),
            'price': '35000.00',
            'is_available': 'on',
            'description': 'Qisqacha tavsif',
            'detailed_information': 'Tasdiqlangan mahsulot yo‘riqnomasi',
            '_save': 'Save',
        })
        self.assertEqual(create_response.status_code, 302)
        product = Product.objects.get(slug='moychechak')
        self.assertTrue(product.image.name.startswith('products/'))

        update_response = self.client.post(f'/admin/catalog/product/{product.pk}/change/', {
            'category': str(category.pk),
            'name': 'Moychechak',
            'slug': 'moychechak',
            'price': '45000.00',
            'description': 'Qisqacha tavsif',
            'detailed_information': 'Yangilangan, tasdiqlangan yo‘riqnoma',
            '_save': 'Save',
            # `is_available` checkbox jo‘natilmagani uchun False bo‘ladi.
        })
        self.assertEqual(update_response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal('45000.00'))
        self.assertFalse(product.is_available)
        self.assertEqual(product.detailed_information, 'Yangilangan, tasdiqlangan yo‘riqnoma')
        api_response = self.client.get('/api/v1/products/moychechak/')
        self.assertEqual(api_response.data['price'], '45000.00')
        self.assertFalse(api_response.data['is_available'])

    def test_regular_user_cannot_access_admin(self):
        customer = get_user_model().objects.create_user(
            username='regular', password='SafePassword!123'
        )
        self.client.force_login(customer)
        response = self.client.get('/admin/catalog/product/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_product_form_shows_current_image_and_loads_local_preview_assets(self):
        category = Category.objects.create(name='Giyohlar', slug='giyohlar')
        product = Product.objects.create(
            category=category,
            name='Moychechak <sinov>',
            slug='moychechak',
            image=self.sample_image(),
            price=Decimal('35000.00'),
            description='Qisqacha tavsif',
            detailed_information='Do‘kon tasdiqlagan qadoq yo‘riqnomasi',
        )
        response = self.client.get(f'/admin/catalog/product/{product.pk}/change/')
        self.assertContains(response, f'data-current-image="{product.image.url}"')
        self.assertContains(response, 'alt="Moychechak &lt;sinov&gt;"')
        self.assertContains(response, 'catalog/admin-image-preview.js')
        self.assertContains(response, 'catalog/admin.css')
        self.assertContains(response, 'Qisqacha tavsif')
        self.assertContains(response, 'Do‘kon tasdiqlagan qadoq yoki yo‘riqnomadagi')
        form = response.context['adminform'].form
        self.assertTrue(form.fields['detailed_information'].required)

    def test_new_product_form_has_preview_without_existing_image(self):
        response = self.client.get('/admin/catalog/product/add/')
        self.assertContains(response, 'data-image-preview')
        self.assertContains(response, 'Rasm tanlanganda shu yerda ko‘rinadi.')
        self.assertNotContains(response, 'data-current-image=')

    def test_staff_without_catalog_permissions_cannot_manage_products(self):
        staff = get_user_model().objects.create_user(
            username='limitedstaff', password='SafeStaffPassword!123', is_staff=True,
        )
        self.client.force_login(staff)
        self.assertEqual(self.client.get('/admin/catalog/product/').status_code, 403)
        self.assertEqual(self.client.get('/admin/catalog/product/add/').status_code, 403)

    def test_superuser_can_delete_product_and_empty_category(self):
        category = Category.objects.create(name='O‘simliklar', slug='osimliklar')
        product = Product.objects.create(
            category=category,
            name='Isiriq',
            slug='isiriq',
            image='products/isiriq.png',
            price=Decimal('12000.00'),
            description='Tavsif',
            detailed_information='Do‘kon tasdiqlagan ma’lumot',
        )
        delete_product = self.client.post(
            f'/admin/catalog/product/{product.pk}/delete/', {'post': 'yes'}
        )
        self.assertEqual(delete_product.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        delete_category = self.client.post(
            f'/admin/catalog/category/{category.pk}/delete/', {'post': 'yes'}
        )
        self.assertEqual(delete_category.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_admin_rejects_non_image_upload(self):
        category = Category.objects.create(name='Giyohlar', slug='giyohlar')
        invalid_file = SimpleUploadedFile('fake.png', b'not a real image', content_type='image/png')
        response = self.client.post('/admin/catalog/product/add/', {
            'category': str(category.pk),
            'name': 'Noto‘g‘ri rasm',
            'slug': 'notogri-rasm',
            'image': invalid_file,
            'price': '10000.00',
            'is_available': 'on',
            'description': 'Tavsif',
            'detailed_information': 'Tasdiqlangan tafsilot',
            '_save': 'Save',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(slug='notogri-rasm').exists())

    def make_translation_product(self):
        category = Category.objects.create(name='Tarjima sinovi', slug='tarjima-sinovi')
        return Product.objects.create(
            category=category, name='Sinov mahsuloti', slug='sinov-mahsuloti',
            image=self.sample_image(), price=Decimal('10000.00'),
            description='Sinov tavsifi', detailed_information='Sinov uchun tasdiqlangan ma’lumot',
        )

    @staticmethod
    def product_form_data(product, **overrides):
        data = {
            'category': str(product.category_id), 'name': product.name, 'slug': product.slug,
            'price': str(product.price), 'description': product.description,
            'detailed_information': product.detailed_information, 'is_available': 'on',
        }
        data.update(overrides)
        return data

    def test_one_admin_form_creates_and_updates_both_languages_with_same_parent(self):
        category_response = self.client.post('/admin/catalog/category/add/', {
            'name': 'Ikki tilli sinov', 'slug': 'ikki-tilli-sinov', 'ru_name': 'Тестовая категория', '_save': 'Save',
        })
        self.assertEqual(category_response.status_code, 302)
        category = Category.objects.get(slug='ikki-tilli-sinov')
        self.assertEqual(category.translations.get(language='ru').name, 'Тестовая категория')
        product = Product.objects.create(
            category=category, name='Sinov', slug='sinov', image=self.sample_image(), price='10000.00',
            description='Sinov tavsifi', detailed_information='Tasdiqlangan sinov ma’lumoti',
        )
        original_id = product.pk
        data = self.product_form_data(
            product, name='Yangilangan sinov', ru_name='Тестовый товар',
            ru_description='Тестовое описание', ru_detailed_information='Проверенные тестовые сведения',
        )
        response = self.client.post(f'/admin/catalog/product/{product.pk}/change/', data)
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.pk, original_id)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(product.name, 'Yangilangan sinov')
        self.assertEqual(product.translations.get(language='uz').name, product.name)
        self.assertEqual(product.translations.get(language='ru').name, 'Тестовый товар')
        form_response = self.client.get(f'/admin/catalog/product/{product.pk}/change/')
        self.assertContains(form_response, 'O‘zbekcha (UZ)')
        self.assertContains(form_response, 'Ruscha (RU)')
        self.assertContains(form_response, 'Тестовый товар')

    def test_partial_russian_product_translation_is_rejected_without_saving_any_changes(self):
        product = self.make_translation_product()
        response = self.client.post(
            f'/admin/catalog/product/{product.pk}/change/',
            self.product_form_data(product, name='Saqlanmagan nom', ru_name='Тестовый товар'),
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['adminform'].form
        self.assertIn('ru_description', form.errors)
        self.assertIn('ru_detailed_information', form.errors)
        product.refresh_from_db()
        self.assertEqual(product.name, 'Sinov mahsuloti')
        self.assertFalse(product.translations.filter(language='ru').exists())

    def test_admin_rejects_whitespace_only_required_uz_text(self):
        product = self.make_translation_product()
        for field in ('name', 'description', 'detailed_information'):
            with self.subTest(field=field):
                form = ProductAdminForm(
                    instance=Product.objects.get(pk=product.pk),
                    data=self.product_form_data(product, **{field: ' \n\t '}),
                )
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
                self.assertIn('Bu maydonni to‘ldiring.', form.errors[field])

    def test_russian_translation_cannot_be_accidentally_erased(self):
        product = self.make_translation_product()
        ProductTranslation.objects.create(
            product=product, language='ru', name='Тестовый товар',
            description='Тестовое описание', detailed_information='Проверенные тестовые сведения',
        )
        response = self.client.post(
            f'/admin/catalog/product/{product.pk}/change/', self.product_form_data(product),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('ru_name', response.context['adminform'].form.errors)
        self.assertTrue(product.translations.filter(language='ru').exists())
        remove_response = self.client.post(
            f'/admin/catalog/product/{product.pk}/change/',
            self.product_form_data(product, remove_ru_translation='on'),
        )
        self.assertEqual(remove_response.status_code, 302)
        self.assertFalse(product.translations.filter(language='ru').exists())
        self.assertTrue(product.translations.filter(language='uz').exists())

    def test_category_russian_translation_uses_explicit_removal(self):
        category = Category.objects.create(name='Sinov', slug='sinov')
        CategoryTranslation.objects.create(category=category, language='ru', name='Тестовая категория')
        data = {'name': category.name, 'slug': category.slug, 'ru_name': ''}
        response = self.client.post(f'/admin/catalog/category/{category.pk}/change/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(category.translations.filter(language='ru').exists())
        response = self.client.post(
            f'/admin/catalog/category/{category.pk}/change/', dict(data, remove_ru_translation='on'),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(category.translations.filter(language='ru').exists())

    def test_form_rolls_back_common_uz_and_ru_changes_if_translation_save_fails(self):
        product = self.make_translation_product()
        form = ProductAdminForm(
            instance=product,
            data=self.product_form_data(
                product, name='Saqlanmagan nom', price='20000.00', ru_name='Тестовый товар',
                ru_description='Тестовое описание', ru_detailed_information='Проверенные тестовые сведения',
            ),
        )
        self.assertTrue(form.is_valid(), form.errors)
        original_save = ProductTranslation.save

        def fail_ru_save(translation, *args, **kwargs):
            if translation.language == 'ru':
                raise RuntimeError('Test translation failure')
            return original_save(translation, *args, **kwargs)

        with patch.object(ProductTranslation, 'save', fail_ru_save), self.assertRaises(RuntimeError):
            form.save()
        product.refresh_from_db()
        self.assertEqual(product.name, 'Sinov mahsuloti')
        self.assertEqual(product.price, Decimal('10000.00'))
        self.assertEqual(product.translations.get(language='uz').name, product.name)
        self.assertFalse(product.translations.filter(language='ru').exists())
