"""Root URL: Django Admin, public catalog va customer authentication API."""

from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from .views import health

admin.site.site_header = 'Herbal Store boshqaruvi'
admin.site.site_title = 'Herbal Store — boshqaruv'
admin.site.index_title = 'Katalog va foydalanuvchilar'

urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.catalog.urls')),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.favorites.urls')),
]

if settings.DEBUG or settings.ENABLE_SWAGGER:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(
            permission_classes=(AllowAny,), authentication_classes=(),
        ), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(
            url_name='schema', permission_classes=(AllowAny,), authentication_classes=(),
        ), name='swagger-ui'),
    ]