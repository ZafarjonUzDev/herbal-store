"""Katalogning v1 public API yo‘llari."""

from django.urls import path

from .views import CategoryListView, CategoryProductsView, ProductDetailView

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path(
        'categories/<slug:category_slug>/products/',
        CategoryProductsView.as_view(),
        name='category-products',
    ),
    path(
        'products/<slug:product_slug>/',
        ProductDetailView.as_view(),
        name='product-detail',
    ),
]
