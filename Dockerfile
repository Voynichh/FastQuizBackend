# syntax=docker/dockerfile:1

# ---- build aşaması: bağımlılıklar ----
FROM python:3.14-slim AS builder
# yerelde docker-compose "dev" verir
ARG REQUIREMENTS=prod
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements/ requirements/
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r requirements/${REQUIREMENTS}.txt

# ---- çalışma aşaması ----
FROM python:3.14-slim AS runtime
ARG REQUIREMENTS=prod
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PORT=8000
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . .
# collectstatic veritabanına bağlanmaz; build için geçici değerler yeterli
RUN if [ "$REQUIREMENTS" = "prod" ] || [ -z "$REQUIREMENTS" ]; then \
      SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.db \
      python manage.py collectstatic --noinput; \
    fi
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]
