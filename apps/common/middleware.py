import time

from django.db import connection
from django.http import JsonResponse

HEALTH_PATH = "/api/v1/health/"
# Kimliksiz uçtan veritabanına gidecek sorgu sayısını sınırlamak için sonuç kısa süre saklanır
HEALTH_CACHE_SECONDS = 5

_cache: dict = {"at": None, "ok": True}


def _database_is_up() -> bool:
    now = time.monotonic()
    if _cache["at"] is not None and now - _cache["at"] < HEALTH_CACHE_SECONDS:
        return _cache["ok"]
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        ok = True
    except Exception:
        ok = False
    _cache.update(at=now, ok=ok)
    return ok


class HealthCheckMiddleware:
    """`/api/v1/health/` isteğini en başta yanıtlar.

    Konteyner orkestratörlerinin ve yük dengeleyicilerin sağlık kontrolü çoğunlukla iç ağdan,
    HTTP üzerinden ve farklı bir Host ile gelir; bu yüzden ALLOWED_HOSTS ve HTTPS
    yönlendirmesinden önce çalışmalıdır. Veritabanı sorgusu en fazla `HEALTH_CACHE_SECONDS`
    saniyede bir (işlem başına) atılır.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTH_PATH and request.method in ("GET", "HEAD"):
            if _database_is_up():
                return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "unavailable"}, status=503)
        return self.get_response(request)
