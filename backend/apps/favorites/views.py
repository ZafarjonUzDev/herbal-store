"""JWT bilan joriy foydalanuvchining saqlangan mahsulotlarini boshqaradi."""

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from apps.catalog.localization import LANGUAGE_PARAMETER, requested_language, with_russian_translations

from .models import SavedProduct
from .serializers import (
    SavedProductCreateSerializer,
    SavedProductReadSerializer,
    SavedProductResultSerializer,
)


@extend_schema_view(
    get=extend_schema(parameters=[LANGUAGE_PARAMETER], responses=SavedProductReadSerializer(many=True)),
    post=extend_schema(
        request=SavedProductCreateSerializer,
        responses={200: SavedProductResultSerializer, 201: SavedProductResultSerializer},
    ),
)
@method_decorator(never_cache, name='dispatch')
class SavedProductListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = SavedProduct.objects.none()
    pagination_class = None

    def get_queryset(self):
        queryset = SavedProduct.objects.filter(user=self.request.user).select_related(
            'product', 'product__category',
        )
        if requested_language({'request': self.request}) == 'ru':
            queryset = with_russian_translations(queryset, 'product__translations')
            queryset = with_russian_translations(queryset, 'product__category__translations')
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SavedProductCreateSerializer
        return SavedProductReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data['product']
        _, created = SavedProduct.objects.get_or_create(user=request.user, product=product)
        return Response(
            {
                'product_id': product.pk,
                'message': 'Mahsulot saqlandi.' if created else 'Mahsulot avval saqlangan.',
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@extend_schema_view(delete=extend_schema(responses={204: None}))
@method_decorator(never_cache, name='dispatch')
class SavedProductDeleteView(generics.DestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = SavedProduct.objects.none()
    serializer_class = SavedProductReadSerializer
    lookup_field = 'product_id'

    def get_queryset(self):
        return SavedProduct.objects.filter(user=self.request.user)
