from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver", "api"]
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
# Vite 5173 doluysa sessizce 5174, 5175... portuna geçer; geliştirmede yerel adreslerin her portu
# kabul edilir (yalnızca dev ayarı; üretimde açık origin listesi kullanılır).
CORS_ALLOWED_ORIGIN_REGEXES = [r"^http://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"]
