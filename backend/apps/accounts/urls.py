"""Customer JWT endpoints; Django Admin o‘zining session auth'idan foydalanadi."""

from django.urls import path

from .views import LoginView, LogoutView, RefreshView, RegisterView, csrf_token_view

urlpatterns = [
    path('auth/csrf/', csrf_token_view, name='auth-csrf'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/token/', LoginView.as_view(), name='auth-token'),
    path('auth/token/refresh/', RefreshView.as_view(), name='auth-token-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
]
