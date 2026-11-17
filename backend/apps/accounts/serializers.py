"""Foydalanuvchi registratsiyasi: Django User va password validatorlari."""

from collections.abc import Mapping

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'password')

    def to_internal_value(self, data):
        # Unique/length validatorlari create_user saqlaydigan NFKC qiymatni tekshiradi.
        if isinstance(data, Mapping) and isinstance(data.get('username'), str):
            data = data.copy()
            data['username'] = User.normalize_username(data['username'])
        return super().to_internal_value(data)

    def validate_username(self, value):
        # DRF matnning ikki chetidagi bo‘sh joylarni standart tarzda olib tashlaydi.
        if not value.strip():
            raise serializers.ValidationError('Username bo‘sh bo‘lishi mumkin emas.')
        return value

    def validate(self, attrs):
        candidate = User(username=attrs['username'])
        try:
            validate_password(attrs['password'], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        # create_user passwordni Django hasheri bilan saqlaydi.
        return User.objects.create_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    def to_internal_value(self, data):
        # Register bilan bir xil NFKC; CharField chetdagi whitespace'ni olib tashlaydi.
        # Normalizatsiya harflarning katta-kichikligini o‘zgartirmaydi.
        if isinstance(data, Mapping) and isinstance(data.get('username'), str):
            data = data.copy()
            data['username'] = User.normalize_username(data['username'])
        return super().to_internal_value(data)
