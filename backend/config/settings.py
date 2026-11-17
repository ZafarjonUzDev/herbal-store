"""Herbal Store MVP: maxfiy qiymatlar environment yoki lokal .env orqali."""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / '.env', override=False)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value in {'true', '1', 'yes', 'on'}:
        return True
    if value in {'false', '0', 'no', 'off'}:
        return False
    raise ImproperlyConfigured(f'{name} must be true/false')


def env_list(name: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, '').split(',') if value.strip()]


def env_positive_int(name: str, default: int) -> int:
    try:
        number = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f'{name} must be a positive integer') from exc
    if number <= 0:
        raise ImproperlyConfigured(f'{name} must be a positive integer')
    return number


DEBUG = env_bool('DJANGO_DEBUG', False)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY or SECRET_KEY.startswith('CHANGE_ME'):
    raise ImproperlyConfigured('Provide a real DJANGO_SECRET_KEY via environment/.env')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('Set DJANGO_ALLOWED_HOSTS when DEBUG=False')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'rest_framework_simplejwt.token_blacklist',
    'apps.accounts.apps.AccountsConfig',
    'apps.catalog.apps.CatalogConfig',
    'apps.favorites.apps.FavoritesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'config.middleware.InterfaceLanguageMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# PostgreSQL: Django va DB bir Docker network ichida bo‘lsa HOST=db.
# Docker yo‘q lokal PostgreSQL uchun .env da POSTGRES_HOST=localhost deb yoziladi.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'herbal_store'),
        'USER': os.getenv('POSTGRES_USER', 'herbal_store'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 0,
    }
}

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'auth_register': '5/hour',
        'auth_login': '10/min',
        'auth_refresh': '30/min',
        'auth_logout': '30/min',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env_positive_int('JWT_ACCESS_MINUTES', 15)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env_positive_int('JWT_REFRESH_DAYS', 7)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Browser auth POST endpointlari CSRF tekshiruvini view dispatch'da bajaradi.
CSRF_FAILURE_VIEW = 'apps.accounts.views.auth_csrf_failure'
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

LANGUAGE_CODE = 'uz'
LANGUAGES = [('uz', 'O‘zbekcha'), ('ru', 'Русский')]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = os.getenv('DJANGO_TIME_ZONE', 'Asia/Tashkent')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Backend porti yopiq; Nginx forwarded proto headerini o‘zi almashtiradi.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SPECTACULAR_SETTINGS = {
    'TITLE': 'Herbal Store API',
    'DESCRIPTION': (
        'Auth POST uchun GET /api/v1/auth/csrf/ orqali cookie/token oling '
        'va X-CSRFToken headerini yuboring. Refresh faqat HttpOnly cookie orqali.'
    ),
    'VERSION': '1.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'APPEND_PATHS': {
        '/api/v1/auth/csrf/': {
            'get': {
                'operationId': 'auth_csrf_retrieve',
                'tags': ['auth'],
                'description': 'CSRF cookie va auth POST uchun masked token beradi.',
                'security': [],
                'responses': {
                    '200': {
                        'description': 'CSRF token',
                        'content': {'application/json': {'schema': {
                            'type': 'object',
                            'required': ['csrfToken'],
                            'properties': {'csrfToken': {'type': 'string'}},
                        }}},
                    },
                },
            },
        },
    },
}
