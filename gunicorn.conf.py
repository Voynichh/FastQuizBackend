import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
worker_class = "gthread"
timeout = 30
graceful_timeout = 20
accesslog = "-"  # loglar stdout'a; App Platform toplar
errorlog = "-"
forwarded_allow_ips = "*"  # TLS, App Platform'un önündeki yük dengeleyicide sonlanır
