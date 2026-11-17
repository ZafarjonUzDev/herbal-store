import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('catalog', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by_users', to='catalog.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_products', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Saqlangan mahsulot',
                'verbose_name_plural': 'Saqlangan mahsulotlar',
                'ordering': ('-created_at', '-id'),
                'constraints': [
                    models.UniqueConstraint(fields=('user', 'product'), name='uniq_saved_product_per_user'),
                ],
            },
        ),
    ]
