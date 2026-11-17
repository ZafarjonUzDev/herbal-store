"""Katalog uchun yagona CRUD joyi — standart Django Admin."""

from django import forms
from django.contrib import admin
from django.db import transaction
from django.utils.html import format_html

from .models import Category, CategoryTranslation, Product, ProductTranslation, TranslationLanguage


class TranslationAdminForm(forms.ModelForm):
    remove_ru_translation = forms.BooleanField(
        label='Ruscha tarjimani o‘chirish', required=False,
        help_text='Faqat mavjud ruscha tarjimani o‘chirish uchun belgilang. O‘zbekcha ma’lumot saqlanadi.',
    )
    translation_model = None
    translation_parent_field = None
    translated_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_ru_translation = None
        if self.instance.pk:
            self.existing_ru_translation = self.instance.translations.filter(language=TranslationLanguage.RU).first()
        if self.existing_ru_translation:
            for field in self.translated_fields:
                self.initial[f'ru_{field}'] = getattr(self.existing_ru_translation, field)
        else:
            self.fields['remove_ru_translation'].widget = forms.HiddenInput()
        for field in self._meta.model._meta.fields:
            if field.name in self.fields:
                self.fields[field.name].error_messages['required'] = 'Bu maydonni to‘ldiring.'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('remove_ru_translation'):
            return cleaned
        populated = [bool(cleaned.get(f'ru_{field}', '').strip()) for field in self.translated_fields]
        if any(populated) and not all(populated):
            for field, present in zip(self.translated_fields, populated):
                if not present:
                    self.add_error(f'ru_{field}', 'Ruscha tarjima uchun barcha ruscha matn maydonlarini to‘ldiring.')
        elif not any(populated) and self.existing_ru_translation:
            self.add_error(
                'ru_name',
                'Mavjud tarjimani bo‘sh saqlab bo‘lmaydi. O‘chirish uchun «Ruscha tarjimani o‘chirish»ni belgilang.',
            )
        return cleaned

    def _save_m2m(self):
        super()._save_m2m()
        parent = {f'{self.translation_parent_field}_id': self.instance.pk}
        manager = self.translation_model.objects.using(self.instance._state.db)
        if self.cleaned_data.get('remove_ru_translation'):
            manager.filter(**parent, language=TranslationLanguage.RU).delete()
        elif self.cleaned_data.get('ru_name'):
            manager.update_or_create(
                **parent, language=TranslationLanguage.RU,
                defaults={field: self.cleaned_data[f'ru_{field}'] for field in self.translated_fields},
            )
        getattr(self.instance, '_prefetched_objects_cache', {}).pop('translations', None)

    def save(self, commit=True):
        # Adminning changeform_view'i ham o‘z tranzaksiyasiga ega; forma alohida ishlatilsa ham izchil saqlanadi.
        with transaction.atomic(using=self.instance._state.db):
            return super().save(commit=commit)


class CategoryAdminForm(TranslationAdminForm):
    ru_name = forms.CharField(label='Kategoriya nomi (RU)', max_length=160, required=False)
    translation_model = CategoryTranslation
    translation_parent_field = 'category'
    translated_fields = ('name',)

    class Meta:
        model = Category
        fields = '__all__'
        labels = {'name': 'Kategoriya nomi', 'slug': 'Manzil nomi (slug)'}
        help_texts = {
            'slug': 'Sahifa manzilida ishlatiladi. Nomdan avtomatik to‘ldiriladi; takrorlanmasin.',
        }


class ProductAdminForm(TranslationAdminForm):
    ru_name = forms.CharField(label='Mahsulot nomi (RU)', max_length=220, required=False)
    ru_description = forms.CharField(
        label='Qisqacha tavsif (RU)', required=False, widget=forms.Textarea(attrs={'rows': 4}),
    )
    ru_detailed_information = forms.CharField(
        label='Batafsil ma’lumot va qo‘llanma (RU)', required=False,
        widget=forms.Textarea(attrs={'rows': 12}),
        help_text=(
            'Ruscha nom va tavsif bilan birga to‘ldiring. Qo‘llash tartibi, cheklovlar va ehtiyot choralarini '
            'do‘kon mas’uli tekshirishi kerak. Avtomatik tarjima ishlatilmaydi.'
        ),
    )
    translation_model = ProductTranslation
    translation_parent_field = 'product'
    translated_fields = ('name', 'description', 'detailed_information')

    class Meta:
        model = Product
        fields = '__all__'
        labels = {
            'category': 'Kategoriya',
            'name': 'Mahsulot nomi',
            'slug': 'Manzil nomi (slug)',
            'image': 'Mahsulot rasmi',
            'price': 'Narxi (so‘m)',
            'is_available': 'Do‘konda mavjud',
            'description': 'Qisqacha tavsif',
            'detailed_information': 'Batafsil ma’lumot va qo‘llanma',
        }
        help_texts = {
            'slug': 'Sahifa manzilida ishlatiladi. Mavjud manzilni o‘zgartirsangiz, eski havola ishlamaydi.',
            'image': 'JPG, JPEG, PNG yoki WebP. Rasm hajmi 5 MiB dan oshmasin.',
            'price': 'Narxni so‘mda kiriting. Manfiy qiymat kiritish mumkin emas.',
            'description': 'Mahsulot haqida qisqa tanishtiruv. To‘liq yo‘riqnomani quyida yozing.',
            'detailed_information': (
                'Majburiy. Do‘kon tasdiqlagan qadoq yoki yo‘riqnomadagi ma’lumotlarni kiriting. '
                'Yo‘riqnoma bo‘lmasa, tasdiqlangan batafsil izoh yozing. Oddiy matn va yangi satrlardan foydalaning.'
            ),
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'detailed_information': forms.Textarea(attrs={'rows': 12}),
        }


class CategoryListFilter(admin.RelatedFieldListFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = 'Kategoriya'


class AvailabilityListFilter(admin.BooleanFieldListFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = 'Do‘konda mavjudligi'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ('category_name', 'slug', 'russian_translation_status', 'updated_on')
    search_fields = ('name', 'translations__name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_on', 'updated_on')
    fieldsets = (
        ('Umumiy ma’lumotlar', {'fields': ('slug',)}),
        ('O‘zbekcha (UZ)', {'fields': ('name',)}),
        ('Ruscha (RU)', {
            'fields': ('ru_name', 'remove_ru_translation'),
            'description': 'Ruscha tarjima ixtiyoriy. Kiritilmaguncha saytda tarjima yetishmasligi ochiq ko‘rsatiladi.',
        }),
        ('Yozuv sanalari', {'fields': ('created_on', 'updated_on'), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')

    @admin.display(description='Ruscha tarjima')
    def russian_translation_status(self, obj):
        return 'Kiritilgan' if any(item.language == TranslationLanguage.RU for item in obj.translations.all()) else 'Kiritilmagan'

    @admin.display(description='Kategoriya nomi', ordering='name')
    def category_name(self, obj):
        return obj.name

    @admin.display(description='Yaratilgan sana', ordering='created_at')
    def created_on(self, obj):
        return obj.created_at

    @admin.display(description='Yangilangan sana', ordering='updated_at')
    def updated_on(self, obj):
        return obj.updated_at


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('product_name', 'product_category', 'product_price', 'availability', 'russian_translation_status', 'updated_on')
    list_filter = (('category', CategoryListFilter), ('is_available', AvailabilityListFilter))
    search_fields = ('name', 'translations__name')
    prepopulated_fields = {'slug': ('name',)}
    list_select_related = ('category',)
    readonly_fields = ('image_preview', 'created_on', 'updated_on')
    fieldsets = (
        ('Umumiy ma’lumotlar', {
            'fields': ('category', 'slug', 'image', 'image_preview', 'price', 'is_available'),
        }),
        ('O‘zbekcha (UZ)', {
            'fields': ('name', 'description', 'detailed_information'),
        }),
        ('Ruscha (RU)', {
            'fields': ('ru_name', 'ru_description', 'ru_detailed_information', 'remove_ru_translation'),
            'description': (
                'Barcha ruscha maydonlarni birga to‘ldiring yoki yangi tarjima uchun ularni bo‘sh qoldiring. '
                'Mazmunini do‘kon mas’uli tekshirishi kerak.'
            ),
        }),
        ('Yozuv sanalari', {
            'fields': ('created_on', 'updated_on'),
            'classes': ('collapse',),
        }),
    )

    class Media:
        js = ('catalog/admin-image-preview.js',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')

    @admin.display(description='Ruscha tarjima')
    def russian_translation_status(self, obj):
        return 'Kiritilgan' if any(item.language == TranslationLanguage.RU for item in obj.translations.all()) else 'Kiritilmagan'

    @admin.display(description='Mahsulot nomi', ordering='name')
    def product_name(self, obj):
        return obj.name

    @admin.display(description='Kategoriya', ordering='category__name')
    def product_category(self, obj):
        return obj.category

    @admin.display(description='Narxi (so‘m)', ordering='price')
    def product_price(self, obj):
        return obj.price

    @admin.display(description='Do‘konda mavjud', boolean=True, ordering='is_available')
    def availability(self, obj):
        return obj.is_available

    @admin.display(description='Rasm ko‘rinishi')
    def image_preview(self, obj):
        if obj and obj.image:
            return format_html(
                '<figure class="product-image-preview" data-image-preview>'
                '<img src="{}" alt="{}" data-current-image="{}">'
                '<figcaption aria-live="polite">Mavjud rasm</figcaption></figure>',
                obj.image.url, obj.name, obj.image.url,
            )
        return format_html(
            '<figure class="product-image-preview" data-image-preview>'
            '<img alt="{}" hidden>'
            '<figcaption aria-live="polite">Rasm tanlanganda shu yerda ko‘rinadi.</figcaption></figure>',
            'Mahsulot rasmi',
        )

    @admin.display(description='Yaratilgan sana', ordering='created_at')
    def created_on(self, obj):
        return obj.created_at

    @admin.display(description='Yangilangan sana', ordering='updated_at')
    def updated_on(self, obj):
        return obj.updated_at
