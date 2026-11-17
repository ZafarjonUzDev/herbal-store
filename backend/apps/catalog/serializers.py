"""Faqat ommaga kerak bo‘lgan ma’lumotni qaytaruvchi serializerlar."""

from rest_framework import serializers

from .models import Category, Product
from .localization import LocalizedCatalogMixin


class CategoryListSerializer(LocalizedCatalogMixin, serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'language', 'translation_available')


class CategoryReferenceSerializer(LocalizedCatalogMixin, serializers.ModelSerializer):
    """Mahsulot detaili ichidagi minimal kategoriya rekvizitlari."""

    class Meta:
        model = Category
        fields = ('name', 'slug', 'language', 'translation_available')


class CategoryProductSerializer(LocalizedCatalogMixin, serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'image', 'price', 'is_available', 'language', 'translation_available')


class CategoryProductsResponseSerializer(serializers.Serializer):
    category = CategoryListSerializer()
    products = CategoryProductSerializer(many=True)


class ProductDetailSerializer(LocalizedCatalogMixin, serializers.ModelSerializer):
    category = CategoryReferenceSerializer(read_only=True)
    description = serializers.CharField(read_only=True, allow_null=True)
    detailed_information = serializers.CharField(read_only=True, allow_null=True)
    translated_fields = ('name', 'description', 'detailed_information')

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'category', 'image', 'price',
            'is_available', 'description', 'detailed_information',
            'language', 'translation_available',
        )
