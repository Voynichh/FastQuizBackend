from .base import *  # noqa: F403
from .base import MIDDLEWARE

DEBUG = False

# TLS, uygulamanın önündeki ters proxy / yük dengeleyicide sonlanır.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# WhiteNoise: Swagger UI statik dosyaları imajdan sunulur.
MIDDLEWARE = [
    MIDDLEWARE[0],  # HealthCheckMiddleware en başta kalır
    MIDDLEWARE[1],  # SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[2:],
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DATABASES["default"]["OPTIONS"] = {"sslmode": "require", "pool": True}  # noqa: F405

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
