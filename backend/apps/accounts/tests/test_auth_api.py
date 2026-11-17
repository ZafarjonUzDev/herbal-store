"""Auth API contract: cookie/JWT/CSRF/rotation va xavfsizlik chegaralari."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import aware_utcnow

from apps.accounts.views import refresh_cookie_name

User = get_user_model()


@override_settings(DEBUG=True)
class AuthAPIContractTests(TestCase):
    def setUp(self):
        # ScopedRateThrottle cache identifikatorlari testlar orasida aralashib ketmasin.
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf = self.client.get('/api/v1/auth/csrf/').json()['csrfToken']

    def post(self, path, payload=None, *, include_csrf=True, **headers):
        if include_csrf:
            headers['HTTP_X_CSRFTOKEN'] = self.csrf
        return self.client.post(path, data=payload or {}, format='json', **headers)

    def register(self, username='herbal_customer', password='SafePassword123!'):
        return self.post('/api/v1/auth/register/', {'username': username, 'password': password})

    def login(self, username='herbal_customer', password='SafePassword123!'):
        return self.post('/api/v1/auth/token/', {'username': username, 'password': password})

    def test_csrf_endpoint_sets_cookie_without_returning_credentials(self):
        response = self.client.get('/api/v1/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['csrfToken'])
        self.assertIn('csrftoken', response.cookies)
        self.assertNotIn('access', response.json())
        self.assertNotIn('refresh', response.json())
        self.assertIn('no-store', response['Cache-Control'])

    def test_each_auth_post_requires_csrf(self):
        for path, payload in (
            ('/api/v1/auth/register/', {'username': 'user1', 'password': 'SafePassword123!'}),
            ('/api/v1/auth/token/', {'username': 'user1', 'password': 'SafePassword123!'}),
            ('/api/v1/auth/token/refresh/', {}),
            ('/api/v1/auth/logout/', {}),
        ):
            with self.subTest(path=path):
                response = self.post(path, payload, include_csrf=False)
                self.assertEqual(response.status_code, 403)

    def test_registration_requires_csrf_even_with_drf_api_view(self):
        response = self.post(
            '/api/v1/auth/register/',
            {'username': 'guest', 'password': 'SafePassword123!'},
            include_csrf=False,
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('detail', response.json())
        self.assertFalse(User.objects.filter(username='guest').exists())

    def test_registration_rejects_untrusted_origin(self):
        response = self.post(
            '/api/v1/auth/register/',
            {'username': 'guest', 'password': 'SafePassword123!'},
            HTTP_ORIGIN='https://untrusted.example',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='guest').exists())

    def test_registration_issues_access_and_refresh_cookie_not_json_refresh(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['username'], 'herbal_customer')
        self.assertTrue(response.data['access'])
        self.assertNotIn('refresh', response.data)
        cookie = response.cookies[refresh_cookie_name()]
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Strict')
        self.assertEqual(cookie['path'], '/api/v1/auth/')
        self.assertFalse(cookie['secure'])  # DEBUG=True: faqat lokal development
        self.assertTrue(User.objects.get(username='herbal_customer').check_password('SafePassword123!'))

    def test_registration_cannot_create_staff_or_superuser(self):
        response = self.post(
            '/api/v1/auth/register/',
            {'username': 'regular_customer', 'password': 'SafePassword123!', 'is_staff': True, 'is_superuser': True},
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='regular_customer')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_registration_rejects_weak_password_and_duplicate_username(self):
        invalid = self.register(username='another_customer', password='1234')
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('password', invalid.data)
        self.register(username='another_customer')
        duplicate = self.register(username='another_customer')
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('username', duplicate.data)

    def test_username_whitespace_trim_and_case_sensitivity(self):
        response = self.register(username='  Flower  ')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username='Flower').exists())
        self.assertEqual(self.register(username='flower').status_code, 201)
        self.assertEqual(User.objects.count(), 2)

    def test_login_requires_csrf_and_invalid_credentials_do_not_leak_username(self):
        User.objects.create_user(username='herbal_customer', password='SafePassword123!')
        no_csrf = self.post('/api/v1/auth/token/', {
            'username': 'herbal_customer', 'password': 'SafePassword123!'
        }, include_csrf=False)
        self.assertEqual(no_csrf.status_code, 403)
        bad = self.login(password='bad-password')
        self.assertEqual(bad.status_code, 401)
        self.assertNotIn('refresh', bad.data)

    def test_login_sets_cookie_and_access_with_no_refresh_in_body(self):
        User.objects.create_user(username='herbal_customer', password='SafePassword123!')
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertIn(refresh_cookie_name(), response.cookies)

    def test_refresh_requires_cookie_not_body_and_csrf(self):
        self.register()
        blocked = self.post('/api/v1/auth/token/refresh/', include_csrf=False)
        self.assertEqual(blocked.status_code, 403)
        existing_cookie = self.client.cookies[refresh_cookie_name()].value
        self.client.cookies.pop(refresh_cookie_name(), None)
        body_only = self.post('/api/v1/auth/token/refresh/', {'refresh': existing_cookie})
        self.assertEqual(body_only.status_code, 401)

    def test_refresh_rotates_cookie_and_old_token_is_revoked(self):
        self.register()
        name = refresh_cookie_name()
        first_refresh = self.client.cookies[name].value
        response = self.post('/api/v1/auth/token/refresh/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {'access'})
        rotated = response.cookies[name].value
        self.assertNotEqual(first_refresh, rotated)
        self.client.cookies[name] = first_refresh
        replay = self.post('/api/v1/auth/token/refresh/')
        self.assertEqual(replay.status_code, 401)

    def test_disabled_user_cannot_refresh(self):
        self.register()
        user = User.objects.get(username='herbal_customer')
        user.is_active = False
        user.save(update_fields=['is_active'])
        response = self.post('/api/v1/auth/token/refresh/')
        self.assertEqual(response.status_code, 401)

    def test_logout_requires_csrf_blacklists_token_and_removes_cookie(self):
        self.register()
        name = refresh_cookie_name()
        existing_cookie = self.client.cookies[name].value
        blocked = self.post('/api/v1/auth/logout/', include_csrf=False)
        self.assertEqual(blocked.status_code, 403)
        response = self.post('/api/v1/auth/logout/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(int(response.cookies[name]['max-age']), 0)
        self.client.cookies[name] = existing_cookie
        replay = self.post('/api/v1/auth/token/refresh/')
        self.assertEqual(replay.status_code, 401)

    def test_logout_without_refresh_cookie_is_idempotent(self):
        response = self.post('/api/v1/auth/logout/')
        self.assertEqual(response.status_code, 204)

    def test_login_throttle_limits_repeated_bad_credentials(self):
        User.objects.create_user(username='herbal_customer', password='SafePassword123!')
        for _ in range(10):
            self.assertEqual(self.login(password='wrong-password').status_code, 401)
        self.assertEqual(self.login(password='wrong-password').status_code, 429)

    def test_auth_endpoints_do_not_accept_get_for_state_changing_operations(self):
        for path in (
            '/api/v1/auth/register/',
            '/api/v1/auth/token/',
            '/api/v1/auth/token/refresh/',
            '/api/v1/auth/logout/',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 405)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_production_cookie_uses_secure_prefix(self):
        response = self.register(username='production_customer')
        self.assertEqual(response.status_code, 201)
        cookie = response.cookies['__Secure-refresh']
        self.assertTrue(cookie['secure'])
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['path'], '/api/v1/auth/')

    def assert_cookie_cleared(self, response):
        cookie = response.cookies[refresh_cookie_name()]
        self.assertFalse(cookie.value)
        self.assertEqual(int(cookie['max-age']), 0)
        self.assertEqual(cookie['path'], '/api/v1/auth/')

    def assert_auth_rejection_preserves_session(self, **headers):
        self.assertEqual(self.register().status_code, 201)
        name = refresh_cookie_name()
        original_refresh = self.client.cookies[name].value
        jti = RefreshToken(original_refresh)['jti']
        outstanding_count = OutstandingToken.objects.count()
        for path, payload in (
            ('/api/v1/auth/register/', {'username': 'blocked_customer', 'password': 'SafePassword123!'}),
            ('/api/v1/auth/token/', {'username': 'herbal_customer', 'password': 'SafePassword123!'}),
            ('/api/v1/auth/token/refresh/', {}),
            ('/api/v1/auth/logout/', {}),
        ):
            with self.subTest(path=path):
                response = self.post(path, payload, **headers)
                self.assertEqual(response.status_code, 403)
                self.assertIn('detail', response.json())
                self.assertNotIn(name, response.cookies)
                # Boolean assertion JWT qiymatini failure outputga chiqarmaydi.
                self.assertTrue(self.client.cookies[name].value == original_refresh)
                self.assertEqual(OutstandingToken.objects.count(), outstanding_count)
                self.assertFalse(BlacklistedToken.objects.filter(token__jti=jti).exists())
                self.assertFalse(User.objects.filter(username='blocked_customer').exists())
        self.assertEqual(self.post('/api/v1/auth/token/refresh/').status_code, 200)

    def test_each_auth_post_rejects_invalid_csrf_without_session_side_effects(self):
        self.assert_auth_rejection_preserves_session(
            include_csrf=False,
            HTTP_X_CSRFTOKEN='0' * 64,
        )

    def test_each_auth_post_rejects_untrusted_origin_without_session_side_effects(self):
        self.assert_auth_rejection_preserves_session(HTTP_ORIGIN='https://untrusted.example')

    def test_registration_rejects_normalized_unicode_duplicate_username(self):
        self.assertEqual(self.register(username='Flower').status_code, 201)
        response = self.register(username='Ｆｌｏｗｅｒ')
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(User.objects.filter(username='Flower').exists())

    def test_login_normalizes_unicode_and_whitespace_like_registration(self):
        typed_username = '  Ｆｌｏｗｅｒ  '
        registered = self.register(username=typed_username)
        self.assertEqual(registered.status_code, 201)
        self.assertEqual(registered.data['user']['username'], 'Flower')
        self.assertEqual(self.post('/api/v1/auth/logout/').status_code, 204)

        logged_in = self.login(username=typed_username)
        self.assertEqual(logged_in.status_code, 200)
        self.assertTrue(logged_in.data['access'])
        self.assertIn(refresh_cookie_name(), logged_in.cookies)
        self.assertEqual(self.post('/api/v1/auth/logout/').status_code, 204)
        self.assertEqual(self.login(username='flower').status_code, 401)

    def test_inactive_user_cannot_login_or_receive_refresh_cookie(self):
        User.objects.create_user(
            username='herbal_customer', password='SafePassword123!', is_active=False
        )
        response = self.login()
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertNotIn(refresh_cookie_name(), response.cookies)
        self.assertEqual(OutstandingToken.objects.count(), 0)

    def test_deleted_user_cannot_refresh_and_cookie_is_cleared(self):
        self.assertEqual(self.register().status_code, 201)
        User.objects.get(username='herbal_customer').delete()
        response = self.post('/api/v1/auth/token/refresh/')
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assert_cookie_cleared(response)

    def test_invalid_or_expired_refresh_is_rejected_and_cookie_is_cleared(self):
        self.assertEqual(self.register().status_code, 201)
        name = refresh_cookie_name()
        expired = RefreshToken(self.client.cookies[name].value)
        expired.set_exp(from_time=aware_utcnow(), lifetime=timedelta(seconds=-1))
        for label, refresh in (('malformed', 'invalid-jwt'), ('expired', str(expired))):
            with self.subTest(token_state=label):
                self.client.cookies[name] = refresh
                response = self.post('/api/v1/auth/token/refresh/')
                self.assertEqual(response.status_code, 401)
                self.assertNotIn('access', response.data)
                self.assertNotIn('refresh', response.data)
                self.assert_cookie_cleared(response)

    def test_invalid_or_expired_logout_is_idempotent_and_cookie_is_cleared(self):
        self.assertEqual(self.register().status_code, 201)
        name = refresh_cookie_name()
        expired = RefreshToken(self.client.cookies[name].value)
        expired.set_exp(from_time=aware_utcnow(), lifetime=timedelta(seconds=-1))
        for label, refresh in (('malformed', 'invalid-jwt'), ('expired', str(expired))):
            with self.subTest(token_state=label):
                self.client.cookies[name] = refresh
                for _ in range(2):
                    response = self.post('/api/v1/auth/logout/')
                    self.assertEqual(response.status_code, 204)
                    self.assertEqual(response.content, b'')
                    self.assert_cookie_cleared(response)
