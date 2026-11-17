"""Mahsulot IDsi bilan joriy foydalanuvchining bookmark API yo‘llari."""

from django.urls import path

from .views import SavedProductDeleteView, SavedProductListCreateView

urlpatterns = [
    path('me/saved-products/', SavedProductListCreateView.as_view(), name='saved-product-list'),
    path(
        'me/saved-products/<int:product_id>/',
        SavedProductDeleteView.as_view(),
        name='saved-product-delete',
    ),
]
