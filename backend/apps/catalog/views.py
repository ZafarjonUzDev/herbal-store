"""Ommaviy katalog: faqat GET, Django Admin uchun yozish API yo‘q."""

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Product
from .localization import LANGUAGE_PARAMETER, requested_language, with_russian_translations
from .serializers import (
    CategoryListSerializer,
    CategoryProductSerializer,
    CategoryProductsResponseSerializer,
    ProductDetailSerializer,
)


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_PARAMETER]))
@method_decorator(never_cache, name='dispatch')
class CategoryListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()  # Public endpoint tokenni talab qilmaydi.
    serializer_class = CategoryListSerializer
    queryset = Category.objects.all()
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        return with_russian_translations(queryset) if requested_language({'request': self.request}) == 'ru' else queryset


@method_decorator(never_cache, name='dispatch')
class CategoryProductsView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(tags=['catalog'], parameters=[LANGUAGE_PARAMETER], responses={200: CategoryProductsResponseSerializer})
    def get(self, request, category_slug):
        categories = Category.objects.all()
        russian = requested_language({'request': request}) == 'ru'
        if russian:
            categories = with_russian_translations(categories)
        category = get_object_or_404(categories, slug=category_slug)
        # Category modelidagi tartib: name, id. Mavjud bo‘lmaganlari ham ko‘rsatiladi.
        products = category.products.all()
        if russian:
            products = with_russian_translations(products)
        return Response({
            'category': CategoryListSerializer(category, context={'request': request}).data,
            'products': CategoryProductSerializer(
                products, many=True, context={'request': request}
            ).data,
        })


@extend_schema_view(get=extend_schema(parameters=[LANGUAGE_PARAMETER]))
@method_decorator(never_cache, name='dispatch')
class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.select_related('category')
    lookup_field = 'slug'
    lookup_url_kwarg = 'product_slug'

    def get_queryset(self):
        queryset = super().get_queryset()
        if requested_language({'request': self.request}) == 'ru':
            queryset = with_russian_translations(queryset)
            queryset = with_russian_translations(queryset, 'category__translations')
        return queryset
