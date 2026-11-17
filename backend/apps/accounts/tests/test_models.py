from django.contrib.auth import get_user_model
from django.test import TestCase


class CustomUserTests(TestCase):
    def test_user_password_is_hashed(self):
        user = get_user_model().objects.create_user(
            username='test_customer', password='SafeSamplePassword!123'
        )
        self.assertNotEqual(user.password, 'SafeSamplePassword!123')
        self.assertTrue(user.check_password('SafeSamplePassword!123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_superuser_is_staff_and_superuser(self):
        user = get_user_model().objects.create_superuser(
            username='test_admin', password='SafeSamplePassword!123'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
