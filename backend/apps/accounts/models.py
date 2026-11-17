"""User boshidan custom model: Django birinchi migrationidan oldin."""
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """MVP login identifikatori: username; parol Django hash formatida."""
    pass
