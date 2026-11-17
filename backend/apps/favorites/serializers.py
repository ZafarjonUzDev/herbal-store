"""Saqlash uchun product ID, ro‘yxat uchun katalogning joriy ma’lumotlari."""

from rest_framework import serializers

from apps.catalog.models import Product
from apps.catalog.serializers import CategoryProductSerializer, CategoryReferenceSerializer

from .models import SavedProduct


class ProductIdField(serializers.PrimaryKeyRelatedField):
    default_error_messages = {
        'invalid': 'product_id musbat butun son bo‘lishi kerak.',
    }

    def to_internal_value(self, data):
        # JSON bool/float/string IDga aylantirilmaydi; bigint chegarasi tekshiriladi.
        if type(data) is not int or not 0 < data <= 9223372036854775807:
            self.fail('invalid')
        return super().to_internal_value(data)


class SavedProductCreateSerializer(serializers.Serializer):
    product_id = ProductIdField(source='product', queryset=Product.objects.all())


class SavedProductReadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='product_id', read_only=True)
    name = serializers.CharField(source='product.name', read_only=True, allow_null=True)
    slug = serializers.SlugField(source='product.slug', read_only=True)
    category = CategoryReferenceSerializer(source='product.category', read_only=True)
    image = serializers.ImageField(source='product.image', read_only=True)
    price = serializers.DecimalField(
        source='product.price', max_digits=12, decimal_places=2, read_only=True,
    )
    is_available = serializers.BooleanField(source='product.is_available', read_only=True)
    saved_at = serializers.DateTimeField(source='created_at', read_only=True)
    language = serializers.ChoiceField(choices=['uz', 'ru'], read_only=True, required=False)
    translation_available = serializers.BooleanField(read_only=True, required=False)

    class Meta:
        model = SavedProduct
        fields = (
            'id', 'name', 'slug', 'category', 'image', 'price',
            'is_available', 'saved_at',
            'language', 'translation_available',
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        localized = CategoryProductSerializer(instance.product, context=self.context).data
        for field in ('name', 'language', 'translation_available'):
            if field in localized:
                data[field] = localized[field]
        return data


class SavedProductResultSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(read_only=True)
    message = serializers.CharField(read_only=True)
