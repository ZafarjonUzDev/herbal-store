"""Lokal demo katalog yaratilishi va mavjud admin ma’lumotlari saqlanishi."""

from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from PIL import Image

from apps.catalog.models import Category, Product


class SeedDemoTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()
        self.addCleanup(self.media_dir.cleanup)
        self.addCleanup(self.media_settings.disable)

    @override_settings(DEBUG=False)
    def test_non_debug_run_refuses_before_creating_records_or_images(self):
        with self.assertRaisesMessage(CommandError, 'DEBUG=True'):
            call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(list(Path(self.media_dir.name).rglob('*.png')), [])

    @override_settings(DEBUG=True)
    def test_repeat_preserves_admin_changes_and_creates_no_duplicate_records_or_images(self):
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(Product.objects.count(), 6)
        self.assertTrue(Product.objects.filter(is_available=False).exists())
        for product in Product.objects.all():
            product.full_clean()
            self.assertIn('namuna', product.name)
            self.assertIn('DEMO', product.detailed_information)
            with product.image.open('rb') as image_file:
                with Image.open(image_file) as image:
                    self.assertEqual(image.format, 'PNG')
                    image.verify()

        product = Product.objects.get(slug='demo-moychechak')
        image_name = product.image.name
        Product.objects.filter(pk=product.pk).update(
            name='Admin tahrirlagan nom', price=Decimal('11111.11'),
            description='Admin tavsifi', detailed_information='Admin tasdiqlagan ma’lumot',
        )
        category = Category.objects.get(slug='demo-giyohlar')
        Category.objects.filter(pk=category.pk).update(name='Admin kategoriya nomi')

        call_command('seed_demo', stdout=StringIO())

        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(Product.objects.count(), 6)
        product.refresh_from_db()
        category.refresh_from_db()
        self.assertEqual(product.name, 'Admin tahrirlagan nom')
        self.assertEqual(product.price, Decimal('11111.11'))
        self.assertEqual(product.description, 'Admin tavsifi')
        self.assertEqual(product.detailed_information, 'Admin tasdiqlagan ma’lumot')
        self.assertEqual(product.image.name, image_name)
        self.assertEqual(category.name, 'Admin kategoriya nomi')
        self.assertEqual(len(list(Path(self.media_dir.name).rglob('*.png'))), 6)
