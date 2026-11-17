"""PostgreSQLda tekshiriladigan katalog integrity qoidalari."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.models import Category, Product


class CatalogModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Giyohlar', slug='giyohlar')

    def make_product(self, **overrides):
        data = {
            'category': self.category,
            'name': 'Moychechak',
            'slug': 'moychechak',
            'image': 'products/moychechak.jpg',
            'price': Decimal('35000.00'),
            'is_available': True,
            'description': 'Qisqacha tavsif.',
            'detailed_information': 'Tasdiqlangan mahsulot yo‘riqnomasi.',
        }
        data.update(overrides)
        return Product.objects.create(**data)

    def test_category_and_product_str_and_ordering(self):
        Category.objects.create(name='Anor', slug='anor')
        self.assertEqual(list(Category.objects.values_list('name', flat=True)), ['Anor', 'Giyohlar'])
        product = self.make_product()
        self.assertEqual(str(product), 'Moychechak')
        self.assertEqual(str(self.category), 'Giyohlar')

    def test_category_name_and_slug_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name='Giyohlar', slug='boshqa')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name='Boshqa', slug='giyohlar')

    def test_product_slug_must_be_unique(self):
        self.make_product()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_product(name='Boshqa', slug='moychechak')

    def test_category_with_products_cannot_be_deleted(self):
        self.make_product()
        with self.assertRaises(ProtectedError):
            self.category.delete()
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_negative_price_rejected_by_db_even_without_full_clean(self):
        product = self.make_product()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.filter(pk=product.pk).update(price=Decimal('-0.01'))
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal('35000.00'))

    def test_negative_price_rejected_by_model_validation(self):
        product = Product(
            category=self.category,
            name='Xato narx',
            slug='xato-narx',
            image=SimpleUploadedFile('sample.jpg', b'fake-image-for-model-validation'),
            price=Decimal('-1.00'),
            description='Tavsif',
            detailed_information='Batafsil',
        )
        with self.assertRaises(ValidationError) as caught:
            product.full_clean()
        self.assertIn('price', caught.exception.message_dict)

    def test_description_and_detailed_information_required(self):
        product = Product(
            category=self.category,
            name='Test mahsulot',
            slug='test-mahsulot',
            image=SimpleUploadedFile('sample.jpg', b'fake-image-for-model-validation'),
            price=Decimal('10.00'),
            description='',
            detailed_information='',
        )
        with self.assertRaises(ValidationError) as caught:
            product.full_clean()
        self.assertIn('description', caught.exception.message_dict)
        self.assertIn('detailed_information', caught.exception.message_dict)

    def test_oversized_image_rejected_by_model_validation(self):
        uploaded_image = SimpleUploadedFile('sample.jpg', b'x' * (5 * 1024 * 1024 + 1))
        product = Product(
            category=self.category,
            name='Katta rasm',
            slug='katta-rasm',
            image=uploaded_image,
            price=Decimal('10.00'),
            description='Tavsif',
            detailed_information='Batafsil',
        )
        with self.assertRaises(ValidationError) as caught:
            product.full_clean()
        self.assertIn('image', caught.exception.message_dict)

    def test_unavailable_product_is_not_deleted(self):
        product = self.make_product(is_available=False)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertFalse(product.is_available)

    def test_product_slug_remains_stable_when_name_changes(self):
        product = self.make_product()
        product.name = 'Moychechak dorivor giyohi'
        product.save(update_fields=['name', 'updated_at'])
        product.refresh_from_db()
        self.assertEqual(product.slug, 'moychechak')
