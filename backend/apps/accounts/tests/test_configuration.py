from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase


class FoundationConfigurationTests(SimpleTestCase):
    def test_custom_user_is_registered(self):
        self.assertEqual(settings.AUTH_USER_MODEL, 'accounts.User')
        self.assertIs(get_user_model(), apps.get_model('accounts', 'User'))

    def test_required_apps_are_installed(self):
        for app in ('accounts', 'catalog', 'favorites', 'rest_framework'):
            with self.subTest(app=app):
                self.assertTrue(apps.is_installed(app) if app == 'rest_framework' else apps.get_app_config(app))

    def test_postgresql_engine_configured(self):
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')

    def test_jwt_authentication_configured(self):
        self.assertIn('rest_framework_simplejwt.authentication.JWTAuthentication', settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'])
