# Django 5.2 model formatiga mos dastlabki katalog migratsiyasi.
# Hozirgi muhitda Django o‘rnatilmagani uchun migrate/makemigrations check zarur.
from decimal import Decimal

import apps.catalog.models
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=160, unique=True)),
                ('slug', models.SlugField(max_length=180, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Kategoriya',
                'verbose_name_plural': 'Kategoriyalar',
                'ordering': ('name', 'id'),
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=220)),
                ('slug', models.SlugField(max_length=230, unique=True)),
                ('image', models.ImageField(max_length=255, upload_to='products/', validators=[
                    django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
                    apps.catalog.models.validate_product_image_size,
                ])),
                ('price', models.DecimalField(decimal_places=2, max_digits=12, validators=[
                    django.core.validators.MinValueValidator(Decimal('0.00')),
                ])),
                ('is_available', models.BooleanField(default=True)),
                ('description', models.TextField()),
                ('detailed_information', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='catalog.category')),
            ],
            options={
                'verbose_name': 'Mahsulot',
                'verbose_name_plural': 'Mahsulotlar',
                'ordering': ('name', 'id'),
                'constraints': [
                    models.CheckConstraint(condition=models.Q(price__gte=0), name='product_price_nonnegative'),
                ],
            },
        ),
    ]
