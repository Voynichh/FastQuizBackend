# Fast Quiz — Backend

[![CI](https://github.com/Voynichh/FastQuizBackend/actions/workflows/ci.yml/badge.svg)](https://github.com/Voynichh/FastQuizBackend/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Fast Quiz**, her sorunun yalnızca **5 saniyede** cevaplanabildiği, üyeliksiz bir bilgi yarışması oyunudur. Bu repo oyunun REST API'sidir; süre, puan ve sıralama kurallarının tamamı burada, sunucu tarafında işler.

> Web arayüzü: **[FastQuizFrontend](https://github.com/Voynichh/FastQuizFrontend)** (Vue 3 + TypeScript). Mobil (Capacitor) aynı API'yi kullanacak şekilde tasarlandı.

## Öne çıkanlar

- **Sunucu tarafı zamanlayıcı:** Süre, soru istemciye verildiği anda (`served_at`) başlar ve sunucuda ölçülür; istemci sayacı yalnızca görseldir. 500 ms ağ toleransı vardır, süresi geçen cevap `timeout` sayılır.
- **Hile önleme:** Doğru şık soru yanıtında asla yer almaz, sorular tek tek verilir, her soruya tek cevap kabul edilir, skor kaydında puan istemciden değil oturumdan okunur.
- **Eşzamanlılık güvenliği:** Cevap kaydı `SELECT … FOR UPDATE` ile kilitlenen transaction içinde yapılır (aynı soruya eşzamanlı iki istek → tek kayıt; thread'li testle kanıtlı).
- **Üyeliksiz kimlik:** Oturum başına `secrets.token_urlsafe(32)` token'ı, veritabanında yalnızca SHA-256 özeti; `hmac.compare_digest` ile karşılaştırma. Çerez ve CSRF yok, mobil istemciyle aynı yöntem.
- **Hız bonuslu puan:** Doğru cevap = 100 + kalan süreye orantılı en fazla 100 bonus (tamsayı aritmetiğiyle, `.5` yukarı yuvarlanır).
- **Skor tablosu:** Kategori bazlı ve genel; sıralama puan ↓, ortalama süre ↑, kayıt zamanı ↑. Bileşik indekslerle okunur.
- **Güvenli takma ad:** Uzunluk/karakter kuralları ve Türkçe + İngilizce küfür filtresi (ı/i, ş/s, leet, harf aralığı ve tekrar numaralarına dayanıklı; "Sikke", "Dickens" gibi masum adlar geçer).
- **Tek hata formatı** (`{"error": {"code", "message", "details"}}`), **IP başına rate limit**, **OpenAPI 3 şeması + Swagger UI**.
- Django Admin'de (`/yonetim/`) soru ve şıklar tek ekranda; tam 4 şık ve tek doğru cevap zorunlu.

## Teknoloji

| | |
| --- | --- |
| Dil / çatı | Python 3.14, Django 6.1, Django REST Framework 3.18 |
| Veritabanı | PostgreSQL 18 (kısmi unique index, `FOR UPDATE`; testler de PostgreSQL üzerinde) |
| Şema / dokümantasyon | drf-spectacular + sidecar (Swagger UI) |
| Test | pytest, pytest-django, factory_boy, time-machine · **160+ test**, `services.py` kapsaması ~%97 |
| Kalite | Ruff (lint + format), pip-audit, GitHub Actions (lint → test → Docker build) |
| Konteyner | Docker + docker-compose (çok aşamalı, root olmayan kullanıcı) |

## Hızlı başlangıç

### Docker ile (önerilen, tek komut)

```bash
cp .env.example .env
docker compose up --build
```

Açılışta migrasyonlar uygulanır ve veritabanı boşsa **5 kategori × 40 soru** otomatik yüklenir.

- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/v1/docs/
- Admin için kullanıcı oluştur: `docker compose exec api python manage.py createsuperuser` → http://localhost:8000/yonetim/

### Yerelde (Python ile)

```bash
cp .env.example .env
docker compose up -d db                 # yalnızca PostgreSQL
py -3.14 -m venv .venv                  # Windows; Linux/macOS: python3.14 -m venv .venv
.venv\Scripts\pip install -r requirements/dev.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_questions
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver
```

Web arayüzünü çalıştırmak için [frontend reposuna](https://github.com/Voynichh/FastQuizFrontend) bak.

## API

Tüm yollar `/api/v1/` altındadır; ayrıntılı şema Swagger'da.

| Metot | Yol | Açıklama |
| --- | --- | --- |
| GET | `/categories/` | Aktif kategoriler ve soru sayısı |
| POST | `/sessions/` | Yeni quiz oturumu açar, 20 soru seçer, `session_token` döner |
| GET | `/sessions/{id}/current/` | Sıradaki soru; süreyi başlatır (tekrar çağrıda aynı `deadline`) |
| POST | `/sessions/{id}/answers/` | Aktif soruya cevap (`choice_id: null` = süre doldu) |
| GET | `/sessions/{id}/result/` | Oturum özeti ve tahmini sıralama |
| POST | `/sessions/{id}/score/` | Takma adı alır, skoru tabloya yazar |
| GET | `/leaderboard/?category={slug}` | İlk 10 (kategori yoksa genel) |
| GET | `/health/` | Sağlık kontrolü |

`{id}` içeren uçlar `X-Session-Token` header'ı ister.

## Testler

```bash
.venv\Scripts\python -m pytest                       # tümü (PostgreSQL gerekir: docker compose up -d db)
.venv\Scripts\python -m pytest --cov=apps            # kapsama
.venv\Scripts\python -m ruff check . && .venv\Scripts\python -m ruff format --check .
```

Süreye bağlı testler gerçek bekleme yapmaz; `time-machine` ile saat dondurulur.

## Proje yapısı

```
config/                  ayarlar (base / dev / prod), urls
apps/
├── quiz/                Category, Question, Choice, QuizSession, SessionQuestion
│   ├── services.py      oturum, süre doğrulama, puanlama (tek doğruluk kaynağı)
│   ├── views.py, serializers.py, admin.py
│   └── management/      seed_questions komutu
├── leaderboard/         ScoreEntry, sıralama sorguları, isim filtresi
└── common/              hata formatı, sağlık middleware'i, ortak alanlar
fixtures/                kategori + 200 soru (kaynak: fixtures/sources/*.json)
scripts/                 kaynaktan fixture üreten betik
docs/PROJECT.md          başlangıç proje dokümanı (mimari, veri modeli, API sözleşmesi)
```

## Notlar

- Sorular yapay zekâ yardımıyla yazıldı; yayın öncesi insan gözüyle kontrol edilmesi önerilir. Düzenlemek için `fixtures/sources/*.json` dosyalarını değiştirip `python scripts/build_fixtures.py` çalıştırın (ya da Admin'den düzenleyin).
- Bu proje yerelde çalışan bir portföy projesidir; canlıya alma planı kapsam dışıdır. `config/settings/prod.py`, `Dockerfile` ve `gunicorn.conf.py` üretim benzeri bir çalışma için hazır bırakılmıştır.

## Lisans

[MIT](LICENSE)
