"""Toshkent bosh do‘konining ommaviy, o‘qish uchun ochiq katalog modellari."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, router, transaction
from django.db.models import Q


MAX_PRODUCT_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MiB


class TranslationLanguage(models.TextChoices):
    UZ = 'uz', 'O‘zbekcha'
    RU = 'ru', 'Ruscha'


def validate_translation_text(value):
    if not value.strip():
        raise ValidationError('Matn faqat bo‘sh joylardan iborat bo‘lishi mumkin emas.')


def validate_product_image_size(value):
    """Admin orqali yuklanadigan rasm o‘lchamini cheklaydi."""
    if value.size > MAX_PRODUCT_IMAGE_BYTES:
        raise ValidationError('Rasm hajmi 5 MiB dan oshmasligi kerak.')


class Category(models.Model):
    name = models.CharField('Kategoriya nomi', max_length=160, unique=True)
    slug = models.SlugField('Manzil nomi (slug)', max_length=180, unique=True)
    created_at = models.DateTimeField('Yaratilgan sana', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan sana', auto_now=True)

    class Meta:
        ordering = ('name', 'id')
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            super().save(*args, **kwargs)
            # Eski UZ ustunlari URL/tartiblash bilan moslik uchun asosiy manba bo‘lib qoladi.
            name = type(self).objects.using(using).values_list('name', flat=True).get(pk=self.pk)
            CategoryTranslation.objects.using(using).update_or_create(
                category_id=self.pk, language=TranslationLanguage.UZ, defaults={'name': name},
            )
        getattr(self, '_prefetched_objects_cache', {}).pop('translations', None)


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Kategoriya',
    )
    name = models.CharField('Mahsulot nomi', max_length=220)
    slug = models.SlugField('Manzil nomi (slug)', max_length=230, unique=True)
    image = models.ImageField(
        'Mahsulot rasmi',
        upload_to='products/',
        max_length=255,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_product_image_size,
        ],
    )
    price = models.DecimalField(
        'Narxi (so‘m)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    is_available = models.BooleanField('Do‘konda mavjud', default=True)
    description = models.TextField('Qisqacha tavsif')
    detailed_information = models.TextField('Batafsil ma’lumot va qo‘llanma')
    created_at = models.DateTimeField('Yaratilgan sana', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan sana', auto_now=True)

    class Meta:
        ordering = ('name', 'id')
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name='product_price_nonnegative',
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            super().save(*args, **kwargs)
            values = type(self).objects.using(using).values(
                'name', 'description', 'detailed_information',
            ).get(pk=self.pk)
            ProductTranslation.objects.using(using).update_or_create(
                product_id=self.pk, language=TranslationLanguage.UZ, defaults=values,
            )
        getattr(self, '_prefetched_objects_cache', {}).pop('translations', None)


class CategoryTranslation(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='translations', verbose_name='Kategoriya',
    )
    language = models.CharField('Til', max_length=2, choices=TranslationLanguage.choices)
    name = models.CharField('Kategoriya nomi', max_length=160, validators=[validate_translation_text])

    class Meta:
        verbose_name = 'Kategoriya tarjimasi'
        verbose_name_plural = 'Kategoriya tarjimalari'
        constraints = [
            models.UniqueConstraint(fields=('category', 'language'), name='uniq_category_translation_language'),
            models.CheckConstraint(
                condition=Q(language__in=TranslationLanguage.values), name='category_translation_supported_language',
            ),
            models.CheckConstraint(condition=Q(name__regex=r'\S'), name='category_translation_name_not_blank'),
        ]

    def __str__(self):
        return f'{self.name} ({self.language.upper()})'

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            super().save(*args, **kwargs)
            stored = type(self).objects.using(using).values('category_id', 'language', 'name').get(pk=self.pk)
            if stored['language'] == TranslationLanguage.UZ:
                Category.objects.using(using).filter(pk=stored['category_id']).update(name=stored['name'])


class ProductTranslation(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='translations', verbose_name='Mahsulot',
    )
    language = models.CharField('Til', max_length=2, choices=TranslationLanguage.choices)
    name = models.CharField('Mahsulot nomi', max_length=220, validators=[validate_translation_text])
    description = models.TextField('Qisqacha tavsif', validators=[validate_translation_text])
    detailed_information = models.TextField(
        'Batafsil ma’lumot va qo‘llanma', validators=[validate_translation_text],
    )

    class Meta:
        verbose_name = 'Mahsulot tarjimasi'
        verbose_name_plural = 'Mahsulot tarjimalari'
        constraints = [
            models.UniqueConstraint(fields=('product', 'language'), name='uniq_product_translation_language'),
            models.CheckConstraint(
                condition=Q(language__in=TranslationLanguage.values), name='product_translation_supported_language',
            ),
            models.CheckConstraint(
                condition=Q(name__regex=r'\S') & Q(description__regex=r'\S') & Q(detailed_information__regex=r'\S'),
                name='product_translation_required_text_not_blank',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.language.upper()})'

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            super().save(*args, **kwargs)
            stored = type(self).objects.using(using).values(
                'product_id', 'language', 'name', 'description', 'detailed_information',
            ).get(pk=self.pk)
            if stored['language'] == TranslationLanguage.UZ:
                Product.objects.using(using).filter(pk=stored['product_id']).update(
                    **{field: stored[field] for field in ('name', 'description', 'detailed_information')},
                )
