"""Sayt API tili explicit query orqali, boshqaruv paneli doimo o‘zbekcha."""

from django.http import JsonResponse
from django.utils import translation


class InterfaceLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = 'uz'
        if request.path.startswith('/api/v1/'):
            language = request.GET.get('lang', 'uz')
            if language not in ('uz', 'ru'):
                return JsonResponse({'lang': ['Til uz yoki ru bo‘lishi kerak.']}, status=400)
        request.LANGUAGE_CODE = language
        with translation.override(language):
            response = self.get_response(request)
            response['Content-Language'] = language
            return response
