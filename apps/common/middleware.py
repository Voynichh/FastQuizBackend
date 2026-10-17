from django.db import connection
from django.http import JsonResponse

HEALTH_PATH = "/api/v1/health/"


class HealthCheckMiddleware:
    """`/api/v1/health/` isteğini en başta yanıtlar.

    Konteyner orkestratörlerinin ve yük dengeleyicilerin sağlık kontrolü çoğunlukla iç ağdan,
    HTTP üzerinden ve farklı bir Host ile gelir; bu yüzden ALLOWED_HOSTS ve HTTPS
    yönlendirmesinden önce çalışmalıdır.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTH_PATH and request.method in ("GET", "HEAD"):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            except Exception:
                return JsonResponse({"status": "unavailable"}, status=503)
            return JsonResponse({"status": "ok"})
        return self.get_response(request)
