"""Database uniqueness va relation CASCADE qoidalari."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.catalog.models import Category, Product
from apps.favorites.models import SavedProduct


class SavedProductModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='saved_customer')
        cls.category = Category.objects.create(name='Giyohlar', slug='giyohlar')
        cls.product = Product.objects.create(
            category=cls.category, name='Moychechak', slug='moychechak',
            image='products/moychechak.jpg', price=Decimal('35000.00'),
            description='Qisqa tavsif.', detailed_information='Tasdiqlangan yo‘riqnoma.',
        )

    def test_duplicate_pair_is_rejected_by_database(self):
        SavedProduct.objects.create(user=self.user, product=self.product)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SavedProduct.objects.create(user=self.user, product=self.product)
        self.assertEqual(SavedProduct.objects.count(), 1)

    def test_deleting_product_cascades_to_all_saved_relations(self):
        other = get_user_model().objects.create_user(username='other_customer')
        SavedProduct.objects.create(user=self.user, product=self.product)
        SavedProduct.objects.create(user=other, product=self.product)
        self.product.delete()
        self.assertEqual(SavedProduct.objects.count(), 0)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_deleting_user_cascades_only_their_saved_relations(self):
        other = get_user_model().objects.create_user(username='other_customer')
        SavedProduct.objects.create(user=self.user, product=self.product)
        relation = SavedProduct.objects.create(user=other, product=self.product)
        self.user.delete()
        self.assertEqual(list(SavedProduct.objects.values_list('pk', flat=True)), [relation.pk])
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_unavailable_product_keeps_its_saved_relation(self):
        relation = SavedProduct.objects.create(user=self.user, product=self.product)
        Product.objects.filter(pk=self.product.pk).update(is_available=False)
        self.assertTrue(SavedProduct.objects.filter(pk=relation.pk).exists())
