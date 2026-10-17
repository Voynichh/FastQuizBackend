# Fast Quiz — Backend

Proje dokümanı: `docs/PROJECT.md` (tek doğruluk kaynağı; mimari, veri modeli, API sözleşmesi, puanlama).
Frontend (Vue 3) ayrı repoda: `..\FastQuizFrontend` (bu klasörün kardeşi).

## Kalıcı kurallar
- Puan ve süre hesabı **sadece** `apps/quiz/services.py` içinde yapılır (Faz 3). View/serializer'da puan hesaplanmaz.
- Doğru şık bilgisi soru yanıtına **asla** eklenmez; sadece cevap sonrası döner.
- İstemciden puan alınmaz; skor kaydında yalnızca `player_name` gelir.
- Ham SQL yok, ORM kullan. Testler PostgreSQL üzerinde çalışır (SQLite yok: kısmi index, `FOR UPDATE`).
- Süreye bağlı testlerde gerçek bekleme yok; `time-machine` kullan.
- Kod/identifier İngilizce, kullanıcıya dönen metinler Türkçe. Hata formatı: `{"error": {"code", "message", "details"}}`.
- Python 3.14 (3.15 değil; Django 6.1 henüz desteklemiyor). Paket sürümleri `requirements/*.txt` içinde `==` ile sabit.

## Komutlar (Windows, repo kökünden)
```
docker compose up -d db
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py loaddata fixtures/categories.json
.venv\Scripts\python manage.py runserver
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check . ; .venv\Scripts\python -m ruff format .
```
`.env` için `.env.example` kopyalanır. Admin: `/yonetim/`.

## Soru havuzu
Kaynak: `fixtures/sources/<slug>.json` (`[soru, zorluk, doğru, yanlış1, yanlış2, yanlış3]`). Düzenledikten sonra `.venv\Scripts\python scripts/build_fixtures.py` ile `fixtures/questions_<slug>.json` yeniden üretilir (pk'ler sabit, `loaddata` tekrar çalıştırılabilir). Yeni soruyu listenin sonuna ekle. Yükleme: `loaddata fixtures/categories.json fixtures/questions_*.json`.

## Durum
Faz 0–2 tamam (iskelet, modeller, admin, docker, CI, 5×40 soru). Sorular insan kontrolü bekliyor. Sıradaki: Faz 3 (API).
