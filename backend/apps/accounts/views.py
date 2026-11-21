"""Browser uchun JWT access/refresh-cookie lifecycle; DRF API bilan mos."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.csrf import csrf_failure as django_csrf_failure
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, RegisterSerializer


AUTH_COOKIE_PATH = '/api/v1/auth/'
ACCESS_RESPONSE = inline_serializer(
    name='AccessTokenResponse',
    fields={'access': serializers.CharField()},
)
AUTH_ERROR_RESPONSE = inline_serializer(
    name='AuthErrorResponse',
    fields={'detail': serializers.CharField()},
)
AUTH_VALIDATION_RESPONSE = inline_serializer(
    name='AuthValidationError',
    fields={
        field: serializers.ListField(child=serializers.CharField(), required=False)
        for field in ('username', 'password', 'non_field_errors')
    },
)
CSRF_PARAMETER = OpenApiParameter(
    name='X-CSRFToken',
    location=OpenApiParameter.HEADER,
    type=str,
    required=True,
    description='GET /api/v1/auth/csrf/ qaytargan token; mos CSRF cookie ham yuboriladi.',
)


def refresh_cookie_name():
    # __Secure- prefiksi faqat HTTPS/Secure cookie bilan ishlaydi.
    return 'refresh_token' if settings.DEBUG else '__Secure-refresh'


def set_refresh_cookie(response, refresh):
    response.set_cookie(
        key=refresh_cookie_name(),
        value=str(refresh),
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        path=AUTH_COOKIE_PATH,
        secure=not settings.DEBUG and not settings.ALLOW_INSECURE_COOKIES,
        httponly=True,
        samesite='Strict',
    )


def clear_refresh_cookie(response):
    # Cookie'ni o‘chirishda aynan avvalgi Path ishlatilishi kerak.
    response.delete_cookie(
        refresh_cookie_name(),
        path=AUTH_COOKIE_PATH,
        samesite='Strict',
    )


def auth_csrf_failure(request, reason=''):
    """Auth API uchun xavfsiz JSON 403, Django Admin uchun odatiy sahifa."""
    if request.path.startswith(AUTH_COOKIE_PATH):
        return JsonResponse({'detail': 'CSRF tekshiruvi muvaffaqiyatsiz.'}, status=403)
    return django_csrf_failure(request, reason=reason)


@never_cache
@ensure_csrf_cookie
def csrf_token_view(request):
    """Frontend X-CSRFToken sarlavhasiga qo‘yadigan tokenni qaytaradi."""
    if request.method != 'GET':
        response = JsonResponse({'detail': 'Method not allowed.'}, status=405)
        response['Allow'] = 'GET'
        return response
    return JsonResponse({'csrfToken': get_token(request)})


# APIView.as_view() tashqi csrf_exempt o‘rami bilan keladi.
# Shu sababli himoyani view'ning ichki dispatch metodiga aniq qo‘yamiz.
@method_decorator([csrf_protect, never_cache], name='dispatch')
class CookieAuthView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)

    def get_authenticate_header(self, request):
        # DRF AuthenticationFailedni challenge bo‘lmasa 403ga aylantiradi.
        return 'Bearer realm="api"'


class RegisterView(CookieAuthView):
    throttle_scope = 'auth_register'

    @extend_schema(
        tags=['auth'],
        request=RegisterSerializer,
        parameters=[CSRF_PARAMETER],
        responses={
            201: inline_serializer(
                name='RegistrationResponse',
                fields={
                    'user': inline_serializer(
                        name='RegisteredUser',
                        fields={'id': serializers.IntegerField(), 'username': serializers.CharField()},
                    ),
                    'access': serializers.CharField(),
                },
            ),
            400: AUTH_VALIDATION_RESPONSE,
            403: AUTH_ERROR_RESPONSE,
            429: AUTH_ERROR_RESPONSE,
        },
        description='User yaratadi. Access JSONda, refresh esa HttpOnly cookie orqali beriladi.',
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError as exc:
            # Faqat username bo‘yicha haqiqiy poyga holatini validatsiya xatosiga aylantiramiz.
            if serializer.Meta.model.objects.filter(username=serializer.validated_data['username']).exists():
                raise ValidationError({'username': ['Bu username allaqachon band.']}) from exc
            raise
        refresh = RefreshToken.for_user(user)
        response = Response(
            {'user': {'id': user.pk, 'username': user.username}, 'access': str(refresh.access_token)},
            status=status.HTTP_201_CREATED,
        )
        set_refresh_cookie(response, refresh)
        return response


class LoginView(CookieAuthView):
    throttle_scope = 'auth_login'

    @extend_schema(
        tags=['auth'],
        request=LoginSerializer,
        parameters=[CSRF_PARAMETER],
        responses={
            200: ACCESS_RESPONSE,
            400: AUTH_VALIDATION_RESPONSE,
            401: AUTH_ERROR_RESPONSE,
            403: AUTH_ERROR_RESPONSE,
            429: AUTH_ERROR_RESPONSE,
        },
        description='Username/password bilan kirish. Refresh JSONga chiqmaydi; HttpOnly cookie o‘rnatiladi.',
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        response = Response({'access': serializer.validated_data['access']}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, serializer.validated_data['refresh'])
        return response


class RefreshView(CookieAuthView):
    throttle_scope = 'auth_refresh'

    @extend_schema(
        tags=['auth'],
        request=None,
        parameters=[
            CSRF_PARAMETER,
            OpenApiParameter(
                name='refresh_token',
                location=OpenApiParameter.COOKIE,
                type=str,
                required=True,
                description='Browser yuboradigan HttpOnly refresh cookie. HTTPS production nomi: __Secure-refresh.',
            ),
        ],
        responses={
            200: ACCESS_RESPONSE,
            401: AUTH_ERROR_RESPONSE,
            403: AUTH_ERROR_RESPONSE,
            429: AUTH_ERROR_RESPONSE,
        },
        description='Refresh faqat cookie orqali olinadi. Rotation yangi cookie va JSON access token qaytaradi.',
    )
    def post(self, request):
        refresh = request.COOKIES.get(refresh_cookie_name())
        if not refresh:
            raise AuthenticationFailed('Autentifikatsiyani yangilash mumkin emas.')

        # Simple JWT serializeri is_active, token muddati, rotatsiya va blacklistni tekshiradi.
        serializer = TokenRefreshSerializer(data={'refresh': refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, AuthenticationFailed, get_user_model().DoesNotExist):
            # Expired/blacklisted/deleted/disabled user: cookie tozalanadi, xavfsiz 401.
            response = Response(
                {'detail': 'Autentifikatsiyani yangilash mumkin emas.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_refresh_cookie(response)
            return response
        tokens = serializer.validated_data
        response = Response({'access': tokens['access']}, status=status.HTTP_200_OK)
        if 'refresh' in tokens:
            set_refresh_cookie(response, tokens['refresh'])
        return response


class LogoutView(CookieAuthView):
    throttle_scope = 'auth_logout'

    @extend_schema(
        tags=['auth'],
        request=None,
        parameters=[
            CSRF_PARAMETER,
            OpenApiParameter(
                name='refresh_token',
                location=OpenApiParameter.COOKIE,
                type=str,
                required=False,
                description='HttpOnly refresh cookie; HTTPS production nomi: __Secure-refresh.',
            ),
        ],
        responses={204: None, 403: AUTH_ERROR_RESPONSE, 429: AUTH_ERROR_RESPONSE},
        description='Refreshni bekor qiladi va cookie tozalaydi. Cookie yo‘q yoki eskirgan bo‘lsa ham 204.',
    )
    def post(self, request):
        refresh = request.COOKIES.get(refresh_cookie_name())
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                # Eskirgan yoki ilgari bekor qilingan cookie bilan ham logout idempotent.
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response
