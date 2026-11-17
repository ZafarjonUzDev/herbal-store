"""Favorites kontrakti, JWT va joriy foydalanuvchi chegaralari."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.utils import aware_utcnow

from apps.catalog.models import Category, Product
from apps.favorites.models import SavedProduct


SAVED_URL = '/api/v1/me/saved-products/'


class FavoritesAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='favorites_customer')
        cls.other = get_user_model().objects.create_user(username='other_customer')
        cls.category = Category.objects.create(name='Giyohlar', slug='giyohlar')
        cls.product = Product.objects.create(
            category=cls.category, name='Moychechak', slug='moychechak',
            image='products/moychechak.jpg', price=Decimal('35000.00'),
            description='Qisqa tavsif.', detailed_information='Tasdiqlangan yo‘riqnoma.',
        )
        cls.unavailable = Product.objects.create(
            category=cls.category, name='Yalpiz', slug='yalpiz',
            image='products/yalpiz.webp', price=Decimal('25000.00'),
            is_available=False, description='Yalpiz tavsifi.',
            detailed_information='Tasdiqlangan batafsil ma’lumot.',
        )

    def authenticate(self, user=None):
        token = AccessToken.for_user(user or self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_guest_cannot_list_save_or_delete(self):
        relation = SavedProduct.objects.create(user=self.user, product=self.product)
        responses = (
            self.client.get(SAVED_URL),
            self.client.post(SAVED_URL, {'product_id': self.product.pk}, format='json'),
            self.client.delete(f'{SAVED_URL}{self.product.pk}/'),
        )
        for response in responses:
            self.assertEqual(response.status_code, 401)
        self.assertTrue(SavedProduct.objects.filter(pk=relation.pk).exists())
        self.assertEqual(SavedProduct.objects.count(), 1)

    def test_malformed_and_expired_access_tokens_are_rejected(self):
        expired = AccessToken.for_user(self.user)
        expired.set_exp(from_time=aware_utcnow(), lifetime=timedelta(seconds=-1))
        for label, token in (('malformed', 'invalid-jwt'), ('expired', str(expired))):
            with self.subTest(state=label):
                self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
                self.assertEqual(self.client.get(SAVED_URL).status_code, 401)
        self.assertEqual(SavedProduct.objects.count(), 0)

    def test_disabled_user_cannot_access_favorites(self):
        self.authenticate()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(SAVED_URL).status_code, 401)

    def test_save_is_idempotent_and_uses_current_user(self):
        self.authenticate()
        payload = {'product_id': self.product.pk, 'user_id': self.other.pk}
        first = self.client.post(SAVED_URL, payload, format='json')
        second = self.client.post(SAVED_URL, payload, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data, {'product_id': self.product.pk, 'message': 'Mahsulot saqlandi.'})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data['message'], 'Mahsulot avval saqlangan.')
        relation = SavedProduct.objects.get()
        self.assertEqual(relation.user_id, self.user.pk)
        self.assertEqual(relation.product_id, self.product.pk)

    def test_same_product_can_be_saved_by_different_users(self):
        SavedProduct.objects.create(user=self.other, product=self.product)
        self.authenticate()
        response = self.client.post(SAVED_URL, {'product_id': self.product.pk}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SavedProduct.objects.count(), 2)

    def test_list_is_user_scoped_and_returns_current_product_values(self):
        SavedProduct.objects.create(user=self.user, product=self.product)
        SavedProduct.objects.create(user=self.other, product=self.unavailable)
        Product.objects.filter(pk=self.product.pk).update(
            name='Yangilangan nom', image='products/new.webp',
            price=Decimal('65000.00'), is_available=False,
        )
        self.authenticate()
        response = self.client.get(SAVED_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(set(item), {
            'id', 'name', 'slug', 'category', 'image', 'price', 'is_available', 'saved_at',
        })
        self.assertEqual(item['id'], self.product.pk)
        self.assertEqual(item['name'], 'Yangilangan nom')
        self.assertEqual(item['price'], '65000.00')
        self.assertFalse(item['is_available'])
        self.assertEqual(item['category'], {'name': 'Giyohlar', 'slug': 'giyohlar'})
        self.assertEqual(item['image'], 'http://testserver/media/products/new.webp')
        self.assertTrue(item['saved_at'])
        self.assertIn('no-store', response['Cache-Control'])

    def test_empty_favorites_is_unpaginated_array(self):
        self.authenticate()
        response = self.client.get(SAVED_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_list_orders_by_newest_saved_time_then_id(self):
        older = SavedProduct.objects.create(user=self.user, product=self.product)
        newer = SavedProduct.objects.create(user=self.user, product=self.unavailable)
        self.authenticate()
        response = self.client.get(SAVED_URL)
        self.assertEqual([item['id'] for item in response.data], [self.unavailable.pk, self.product.pk])
        same_time = timezone.now()
        SavedProduct.objects.filter(pk__in=[older.pk, newer.pk]).update(created_at=same_time)
        response = self.client.get(SAVED_URL)
        self.assertEqual([item['id'] for item in response.data], [self.unavailable.pk, self.product.pk])

    def test_unavailable_product_can_be_saved(self):
        self.authenticate()
        response = self.client.post(SAVED_URL, {'product_id': self.unavailable.pk}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(self.client.get(SAVED_URL).data[0]['is_available'])

    def test_invalid_missing_or_unknown_product_id_returns_field_error(self):
        self.authenticate()
        payloads = [
            {}, {'product_id': None}, {'product_id': True}, {'product_id': False},
            {'product_id': str(self.product.pk)}, {'product_id': float(self.product.pk)},
            {'product_id': 1.5}, {'product_id': []}, {'product_id': {}},
            {'product_id': 0}, {'product_id': -1}, {'product_id': 2 ** 63},
            {'product_id': self.unavailable.pk + 1000},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post(SAVED_URL, payload, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('product_id', response.data)
        self.assertEqual(SavedProduct.objects.count(), 0)

    def test_nonobject_or_malformed_json_is_rejected(self):
        self.authenticate()
        response = self.client.post(SAVED_URL, [self.product.pk], format='json')
        self.assertEqual(response.status_code, 400)
        malformed = self.client.post(SAVED_URL, '{"product_id":', content_type='application/json')
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(SavedProduct.objects.count(), 0)

    def test_delete_own_relation_leaves_product_and_other_users_relation(self):
        SavedProduct.objects.create(user=self.user, product=self.product)
        other_relation = SavedProduct.objects.create(user=self.other, product=self.product)
        self.authenticate()
        response = self.client.delete(f'{SAVED_URL}{self.product.pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertTrue(SavedProduct.objects.filter(pk=other_relation.pk).exists())
        self.assertEqual(self.client.delete(f'{SAVED_URL}{self.product.pk}/').status_code, 404)

    def test_other_users_or_missing_relation_cannot_be_deleted(self):
        relation = SavedProduct.objects.create(user=self.other, product=self.product)
        self.authenticate()
        self.assertEqual(self.client.delete(f'{SAVED_URL}{self.product.pk}/').status_code, 404)
        self.assertEqual(self.client.delete(f'{SAVED_URL}{self.unavailable.pk}/').status_code, 404)
        self.assertTrue(SavedProduct.objects.filter(pk=relation.pk).exists())

    def test_list_does_not_make_a_query_per_product_or_category(self):
        SavedProduct.objects.create(user=self.user, product=self.product)
        SavedProduct.objects.create(user=self.user, product=self.unavailable)
        self.client.force_authenticate(user=self.user)
        with self.assertNumQueries(1):
            response = self.client.get(SAVED_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
