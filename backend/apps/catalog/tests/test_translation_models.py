"""Tarjima yozuvlari asosiy obyektlar va saqlangan mahsulotlar aloqasini o‘zgartirmaydi."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.catalog.models import Category, CategoryTranslation, Product, ProductTranslation


class CatalogTranslationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Sinov kategoriyasi', slug='sinov-kategoriyasi')
        cls.product = Product.objects.create(
            category=cls.category, name='Sinov mahsuloti', slug='sinov-mahsuloti',
            image='products/test.png', price=Decimal('12000.00'),
            description='Sinov tavsifi', detailed_information='Sinov uchun tasdiqlangan tafsilot',
        )

    def test_new_parent_creates_exact_uz_translation_and_no_russian_text(self):
        self.assertEqual(self.category.translations.get(language='uz').name, self.category.name)
        translation = self.product.translations.get(language='uz')
        for field in ('name', 'description', 'detailed_information'):
            self.assertEqual(getattr(translation, field), getattr(self.product, field))
        self.assertFalse(CategoryTranslation.objects.filter(language='ru').exists())
        self.assertFalse(ProductTranslation.objects.filter(language='ru').exists())

    def test_existing_uz_fields_and_translation_stay_consistent_without_changing_slug(self):
        product = Product.objects.get(pk=self.product.pk)
        product.name = 'Yangilangan sinov nomi'
        product.save(update_fields=('name', 'updated_at'))
        translation = product.translations.get(language='uz')
        self.assertEqual(translation.name, product.name)
        translation.description = 'Yangilangan sinov tavsifi'
        translation.save()
        product.refresh_from_db()
        self.assertEqual(product.description, translation.description)
        self.assertEqual(product.slug, 'sinov-mahsuloti')
        category_translation = self.category.translations.get(language='uz')
        category_translation.name = 'Yangilangan kategoriya'
        category_translation.save()
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, category_translation.name)

    def test_partial_parent_update_uses_stored_uz_values(self):
        product = Product.objects.get(pk=self.product.pk)
        product.name = 'Saqlanmasligi kerak bo‘lgan nom'
        product.price = Decimal('15000.00')
        product.save(update_fields=('price',))
        self.assertEqual(product.translations.get(language='uz').name, self.product.name)

    def test_partial_translation_update_does_not_overwrite_other_original_fields(self):
        translation = self.product.translations.get(language='uz')
        translation.name = 'Saqlanmasligi kerak bo‘lgan nom'
        translation.description = 'Yangilangan tavsif'
        translation.save(update_fields=('description',))
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Sinov mahsuloti')
        self.assertEqual(self.product.description, 'Yangilangan tavsif')

    def test_category_translation_language_is_unique_and_supported(self):
        for language in ('uz', 'en'):
            with self.subTest(language=language), self.assertRaises(IntegrityError), transaction.atomic():
                CategoryTranslation.objects.create(category=self.category, language=language, name='Sinov')

    def test_product_translation_language_is_unique_and_supported(self):
        for language in ('uz', 'en'):
            with self.subTest(language=language), self.assertRaises(IntegrityError), transaction.atomic():
                ProductTranslation.objects.create(
                    product=self.product, language=language, name='Sinov',
                    description='Sinov tavsifi', detailed_information='Sinov tafsiloti',
                )

    def test_database_rejects_blank_required_translation_fields(self):
        for field in ('name', 'description', 'detailed_information'):
            for blank in ('', '  \n\t'):
                with self.subTest(field=field, blank=blank):
                    values = {'name': 'Sinov', 'description': 'Sinov', 'detailed_information': 'Sinov'}
                    values[field] = blank
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        ProductTranslation.objects.create(product=self.product, language='ru', **values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CategoryTranslation.objects.create(category=self.category, language='ru', name=' \t ')

    def test_translation_model_validation_rejects_whitespace(self):
        translation = ProductTranslation(
            product=self.product, language='ru', name='Sinov', description=' ', detailed_information='Sinov',
        )
        with self.assertRaises(ValidationError) as caught:
            translation.full_clean()
        self.assertIn('description', caught.exception.message_dict)

    def test_translation_cascade_removes_only_deleted_parent_translations(self):
        product_id = self.product.pk
        self.product.delete()
        self.assertFalse(ProductTranslation.objects.filter(product_id=product_id).exists())
        self.assertTrue(CategoryTranslation.objects.filter(category=self.category).exists())


class CatalogTranslationMigrationTests(TransactionTestCase):
    """Faqat Django ajratgan test bazasida eski sxema → yangi sxema tekshiriladi."""

    migrate_from = [('catalog', '0001_initial')]
    migrate_to = [('catalog', '0002_catalog_translations')]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        targets = self.migrate_from + [('accounts', '0001_initial'), ('favorites', '0001_initial')]
        apps = executor.loader.project_state(targets).apps
        category = apps.get_model('catalog', 'Category').objects.create(name='Eski kategoriya', slug='eski-kategoriya')
        product = apps.get_model('catalog', 'Product').objects.create(
            category_id=category.pk, name='Eski mahsulot', slug='eski-mahsulot', image='products/old.png',
            price=Decimal('25000.00'), is_available=False, description='Eski tavsif\nAsl satr',
            detailed_information='Asl, tasdiqlangan qo‘llanma\nIkkinchi satr',
        )
        user = apps.get_model('accounts', 'User').objects.create(username='migration-customer', password='unused')
        saved = apps.get_model('favorites', 'SavedProduct').objects.create(user_id=user.pk, product_id=product.pk)
        self.original_ids = (category.pk, product.pk, user.pk, saved.pk)
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.migrate_to)
        super().tearDown()

    def test_data_migration_keeps_original_text_ids_slugs_and_favorites(self):
        from django.contrib.auth import get_user_model
        from apps.favorites.models import SavedProduct

        category_id, product_id, user_id, saved_id = self.original_ids
        category = Category.objects.get(pk=category_id)
        product = Product.objects.get(pk=product_id)
        self.assertEqual(category.slug, 'eski-kategoriya')
        self.assertEqual(product.slug, 'eski-mahsulot')
        self.assertEqual(product.category_id, category_id)
        self.assertEqual(product.image.name, 'products/old.png')
        self.assertEqual(product.price, Decimal('25000.00'))
        self.assertFalse(product.is_available)
        self.assertEqual(product.description, 'Eski tavsif\nAsl satr')
        self.assertEqual(product.detailed_information, 'Asl, tasdiqlangan qo‘llanma\nIkkinchi satr')
        self.assertEqual(category.translations.get(language='uz').name, 'Eski kategoriya')
        self.assertEqual(product.translations.get(language='uz').description, product.description)
        self.assertEqual(product.translations.get(language='uz').detailed_information, product.detailed_information)
        self.assertFalse(ProductTranslation.objects.filter(language='ru').exists())
        self.assertFalse(CategoryTranslation.objects.filter(language='ru').exists())
        self.assertTrue(get_user_model().objects.filter(pk=user_id, username='migration-customer').exists())
        self.assertTrue(SavedProduct.objects.filter(pk=saved_id, user_id=user_id, product_id=product_id).exists())
