from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "apps.quiz",
    "apps.leaderboard",
]

MIDDLEWARE = [
    # Sağlık kontrolü ALLOWED_HOSTS ve HTTPS yönlendirmesinden önce yanıtlanmalı.
    "apps.common.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS: oturum token'ı header ile taşındığı için çerez gönderilmez.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_HEADERS = [
    "accept",
    "content-type",
    "x-session-token",
    "x-client",
    "x-client-version",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    # IP başına dakikalık sınırlar (Bölüm 7)
    "DEFAULT_THROTTLE_RATES": {
        "session_create": "10/min",
        "answers": "60/min",
        "score": "5/min",
    },
    # Proxy arkasında gerçek istemci IP'si için; yük dengeleyici sayısı biliniyorsa ayarlanır.
    "NUM_PROXIES": env.int("NUM_PROXIES", default=None),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Fast Quiz API",
    "DESCRIPTION": "Fast Quiz web ve mobil istemcileri için durumsuz JSON REST API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    # Swagger UI dosyaları imajdan (sidecar) sunulur, CDN'e bağımlılık yok.
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

# Oyun parametreleri (API yanıtlarında istemciye de döner)
QUIZ_QUESTION_COUNT = env.int("QUIZ_QUESTION_COUNT", default=20)
QUIZ_TIME_LIMIT_MS = env.int("QUIZ_TIME_LIMIT_MS", default=5000)
QUIZ_GRACE_MS = env.int("QUIZ_GRACE_MS", default=500)
LEADERBOARD_SIZE = env.int("LEADERBOARD_SIZE", default=10)
# Bu kadar süre işlem görmeyen aktif oturum "abandoned" olur
QUIZ_SESSION_IDLE_SECONDS = env.int("QUIZ_SESSION_IDLE_SECONDS", default=600)
