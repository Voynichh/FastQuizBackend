from django.http import JsonResponse
from django.views import defaults

from .exceptions import error_body


def _is_api(request):
    return request.path.startswith("/api/")


def not_found(request, exception=None):
    if _is_api(request):
        return JsonResponse(error_body("not_found", "Kayıt bulunamadı."), status=404)
    return defaults.page_not_found(request, exception)


def server_error(request):
    if _is_api(request):
        return JsonResponse(error_body("server_error", "Beklenmeyen bir hata oluştu."), status=500)
    return defaults.server_error(request)
