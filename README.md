# Fast Quiz — Backend

Django 6.1 + DRF + PostgreSQL 18. Ayrıntılar için `docs/PROJECT.md`.

## Yerel kurulum
```
cp .env.example .env
docker compose up -d db
py -3.14 -m venv .venv
.venv\Scripts\pip install -r requirements/dev.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py loaddata fixtures/categories.json
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver
```
Admin: http://localhost:8000/yonetim/

## Test ve kalite
```
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check . && .venv\Scripts\python -m ruff format --check .
```
