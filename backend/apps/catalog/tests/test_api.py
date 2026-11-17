"""Public API javoblari Architecture v1.1 contract'iga mosligini tekshiradi."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product


class CatalogPublicAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.giyohlar = Category.objects.create(name='Giyohlar', slug='giyohlar')
        cls.boshqa = Category.objects.create(name='Anor mahsulotlari', slug='anor-mahsulotlari')
        cls.moychechak = Product.objects.create(
            category=cls.giyohlar,
            name='Moychechak',
            slug='moychechak',
            image='products/moychechak.jpg',
            price=Decimal('35000.00'),
            is_available=True,
            description='Qisqa tavsif.',
            detailed_information='Tarkib va qo‘llanmadagi tasdiqlangan ma’lumot.',
        )
        cls.yalpiz = Product.objects.create(
            category=cls.giyohlar,
            name='Yalpiz',
            slug='yalpiz',
            image='products/yalpiz.webp',
            price=Decimal('25000.00'),
            is_available=False,
            description='Yalpiz tavsifi.',
            detailed_information='Yalpiz to‘g‘risida tasdiqlangan ma’lumot.',
        )

    def test_guest_can_list_categories_in_name_order(self):
        response = self.client.get('/api/v1/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([x['name'] for x in response.data], ['Anor mahsulotlari', 'Giyohlar'])
        self.assertEqual(set(response.data[0]), {'id', 'name', 'slug'})
        self.assertIn('no-store', response['Cache-Control'])

    def test_category_products_contract_and_unavailable_product(self):
        response = self.client.get('/api/v1/categories/giyohlar/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), {'category', 'products'})
        self.assertEqual(response.data['category']['slug'], 'giyohlar')
        self.assertEqual([p['name'] for p in response.data['products']], ['Moychechak', 'Yalpiz'])
        self.assertFalse(response.data['products'][1]['is_available'])
        self.assertEqual(response.data['products'][0]['price'], '35000.00')
        self.assertTrue(response.data['products'][0]['image'].startswith('http://testserver/media/products/'))
        self.assertEqual(
            set(response.data['products'][0]),
            {'id', 'name', 'slug', 'image', 'price', 'is_available'},
        )
        self.assertIn('no-store', response['Cache-Control'])

    def test_empty_category_returns_200_with_empty_products(self):
        response = self.client.get('/api/v1/categories/anor-mahsulotlari/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['products'], [])

    def test_unknown_category_returns_404(self):
        response = self.client.get('/api/v1/categories/noma-lum/products/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_can_view_product_detail_with_category_slug(self):
        response = self.client.get('/api/v1/products/moychechak/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['category'], {'name': 'Giyohlar', 'slug': 'giyohlar'})
        self.assertEqual(response.data['detailed_information'], self.moychechak.detailed_information)
        self.assertEqual(response.data['price'], '35000.00')
        self.assertEqual(
            set(response.data),
            {'id', 'name', 'slug', 'category', 'image', 'price', 'is_available', 'description', 'detailed_information'},
        )
        self.assertIn('no-store', response['Cache-Control'])

    def test_unknown_product_returns_404(self):
        response = self.client.get('/api/v1/products/noma-lum/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_product_write_methods_not_allowed(self):
        paths_and_methods = [
            ('/api/v1/categories/', 'post'),
            ('/api/v1/categories/giyohlar/products/', 'post'),
            ('/api/v1/products/moychechak/', 'put'),
            ('/api/v1/products/moychechak/', 'patch'),
            ('/api/v1/products/moychechak/', 'delete'),
        ]
        for url, method in paths_and_methods:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, {}, format='json')
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_authenticated_customer_cannot_edit_catalog_either(self):
        customer = get_user_model().objects.create_user(username='customer', password='SafePassword!123')
        self.client.force_authenticate(user=customer)
        response = self.client.delete('/api/v1/products/moychechak/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_api_shows_current_price_after_admin_change(self):
        Product.objects.filter(pk=self.moychechak.pk).update(price=Decimal('65000.00'))
        response = self.client.get('/api/v1/products/moychechak/')
        self.assertEqual(response.data['price'], '65000.00')
