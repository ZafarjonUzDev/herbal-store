"""Foydalanuvchi saqlagan mahsulotlar: katalog ma’lumotlari nusxalanmaydi."""

from django.conf import settings
from django.db import models

from apps.catalog.models import Product


class SavedProduct(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_products',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='saved_by_users',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')
        verbose_name = 'Saqlangan mahsulot'
        verbose_name_plural = 'Saqlangan mahsulotlar'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'product'),
                name='uniq_saved_product_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.user_id}: {self.product_id}'
