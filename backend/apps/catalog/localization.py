"""Faqat katalog matnini tanlash; obyekt identifikatorlari va aloqalar umumiy."""

from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers


LANGUAGE_PARAMETER = OpenApiParameter(
    name='lang', type=str, enum=['uz', 'ru'], required=False,
    description=(
        'Standart uz: avvalgi javob shakli saqlanadi. Explicit lang uchun language va '
        'translation_available ham qaytadi. RU tarjimasi yo‘q bo‘lsa matn null, '
        'translation_available=false; UZ matni ruscha o‘rnida berilmaydi.'
    ),
)


def requested_language(context):
    request = context.get('request')
    return request.query_params.get('lang', 'uz') if request is not None else 'uz'


def with_russian_translations(queryset, relation='translations'):
    # Har bir ro‘yxat uchun bitta qo‘shimcha query; N+1 yuzaga kelmaydi.
    related_model = queryset.model
    for part in relation.split('__'):
        related_model = related_model._meta.get_field(part).related_model
    return queryset.prefetch_related(Prefetch(
        relation, queryset=related_model.objects.filter(language='ru'), to_attr='russian_translations',
    ))


class LocalizedCatalogMixin(serializers.Serializer):
    name = serializers.CharField(read_only=True, allow_null=True)
    language = serializers.ChoiceField(choices=['uz', 'ru'], read_only=True, required=False)
    translation_available = serializers.BooleanField(read_only=True, required=False)
    translated_fields = ('name',)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request is None or 'lang' not in request.query_params:
            return data
        language = requested_language(self.context)
        available = True
        if language == 'ru':
            rows = getattr(instance, 'russian_translations', None)
            row = rows[0] if rows else None
            if rows is None:
                row = instance.translations.filter(language='ru').first()
            available = row is not None and all(
                getattr(row, field).strip() for field in self.translated_fields
            )
            for field in self.translated_fields:
                if field in data:
                    data[field] = getattr(row, field) if available else None
        data.update(language=language, translation_available=available)
        return data
