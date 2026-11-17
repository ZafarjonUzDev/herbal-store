"""Ikki parallel Save PostgreSQL UNIQUE poygasini 201/200 bilan yakunlaydi."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.db.models.query import QuerySet
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.catalog.models import Category, Product
from apps.favorites.models import SavedProduct


@skipUnless(connection.vendor == 'postgresql', 'Parallel unique constraint PostgreSQLda tekshiriladi.')
class ConcurrentSaveTests(TransactionTestCase):
    def test_two_parallel_inserts_return_created_and_existing_without_duplicate(self):
        user = get_user_model().objects.create_user(username='parallel_customer')
        category = Category.objects.create(name='Giyohlar', slug='giyohlar')
        product = Product.objects.create(
            category=category, name='Moychechak', slug='moychechak',
            image='products/moychechak.jpg', price=Decimal('35000.00'),
            description='Qisqa tavsif.', detailed_information='Tasdiqlangan yo‘riqnoma.',
        )
        access = str(AccessToken.for_user(user))
        barrier = Barrier(2, timeout=10)
        original_create = QuerySet.create

        def simultaneous_create(queryset, **kwargs):
            if queryset.model is SavedProduct:
                barrier.wait()
            return original_create(queryset, **kwargs)

        def save_product():
            close_old_connections()
            try:
                client = APIClient()
                client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
                response = client.post(
                    '/api/v1/me/saved-products/', {'product_id': product.pk}, format='json',
                )
                return response.status_code, response.data['product_id']
            finally:
                connections.close_all()

        with patch.object(QuerySet, 'create', simultaneous_create):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(save_product) for _ in range(2)]
                results = [future.result(timeout=20) for future in futures]

        self.assertEqual(sorted(code for code, _ in results), [200, 201])
        self.assertEqual([product_id for _, product_id in results], [product.pk, product.pk])
        self.assertEqual(SavedProduct.objects.filter(user=user, product=product).count(), 1)
