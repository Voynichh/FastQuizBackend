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
.venv\Scripts\python manage.py seed_questions
.venv\Scripts\python manage.py runserver
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check . ; .venv\Scripts\python -m ruff format .
```
`.env` için `.env.example` kopyalanır. Yönetim paneli (Django Admin) yoktur; soru içeriği fixture dosyalarından yönetilir.

## Soru havuzu
Kaynak: `fixtures/sources/<slug>.json` (`[soru, zorluk, doğru, yanlış1, yanlış2, yanlış3]`). Düzenledikten sonra `.venv\Scripts\python scripts/build_fixtures.py` ile `fixtures/questions_<slug>.json` yeniden üretilir (pk'ler sabit, `loaddata` tekrar çalıştırılabilir). Yeni soruyu listenin sonuna ekle. Yükleme: `manage.py seed_questions` (veritabanı boşsa yükler; `--force` ile yeniden yükler).

## API notları (doküman Bölüm 6–7'ye ek kararlar)
Şema/Swagger: `/api/v1/schema/`, `/api/v1/docs/` (statik dosyalar `drf-spectacular-sidecar` ile imajdan). Katmanlar: view → `services.py` → model; hata sınıfları `apps/common/exceptions.py`.
- Ek hata kodları: `session_abandoned` (409, 10 dk hareketsizlik; `QUIZ_SESSION_IDLE_SECONDS`), `session_not_completed` (409, result/score tamamlanmamış oturumda), `category_unavailable` (409, havuzda `QUIZ_QUESTION_COUNT`'tan az geçerli soru), `score_rejected` (400, gerçekçi olmayan hız), `forbidden`, `method_not_allowed`, `unsupported_media_type`, `server_error`.
- Geç gelen cevap (`response_ms > limit + grace`) hata değil, 200 + `result: "timeout"` döner. `choice_id: null` her zaman timeout.
- Puan bonusu yarım yukarı yuvarlanır (tamsayı aritmetiği). Ortalama süre: timeout = tam süre, diğerleri en fazla tam süre.
- Sıralama: puan↓, ort. süre↑, `created_at`↑, `id`↑. `estimated_rank` kaydedilmemiş skorda eşitlikte sona koyar, kaydedilmişse gerçek sırayı verir.
- `GET /sessions/{id}/current/` yanıtına ek olarak `total_score` döner (sayfa yenilemede skoru geri yüklemek için). Koleksiyon yanıtları sarılıdır: `{"categories": [...]}`, `{"category": slug|null, "entries": [...]}`.
- Rate limit gerçek bağlantı IP'si başınadır: `NUM_PROXIES` varsayılanı **0** (istemcinin yazabildiği `X-Forwarded-For` yok sayılır; spoof'la limit atlatma güvenlik incelemesinde bulunup kapatıldı, regresyon testi `test_security.py`). Güvenilir bir ters proxy arkasına konulursa gerçek proxy sayısı verilmeli. Sayaçlar işlem başına bellekte (LocMem): çok işçili sunucuda limit işçi sayısı kadar katlanır, paylaşımlı cache gerekir.
- Bot önlemi: ortalama cevap süresi `QUIZ_MIN_PLAUSIBLE_AVG_MS` (700 ms) altındaysa skor tabloya yazılmaz (`score_rejected`, 400); sonuç ekranı yine açılır. Anonim bir quizde tam çözülemeyen bir sınırlamanın hafifletmesidir (doğru şık cevap sonrası açıklandığı için cevap tablosu script'le öğrenilebilir); kimlik/CAPTCHA kapsam dışı.
- Takma ad: yalnızca Latin harf (aksanlılar dahil), ASCII rakam, boşluk ve `_ - .`; Kiril/Yunan homoglifleri reddedilir, ad NFC'ye normalize edilir. Frontend `lib/playerName.ts` aynı kuralı uygular.
- `purge_stale_sessions`: 24 saatten eski bitmemiş ve 7 günden eski kaydedilmemiş oturumları siler (skoru olan oturumlara dokunmaz); `docker compose up` açılışında çalışır. Sağlık ucu veritabanını en fazla 5 sn'de bir sorgular.
- `docker-compose.yml` portları yalnızca loopback'e (127.0.0.1 / ::1) yayımlar.
- `abandoned` işaretleme tembeldir (oturuma bir sonraki istekte); temizlik `purge_stale_sessions` ile.

## Kapsam
Yerelde çalışan portföy projesi; **canlıya alma iptal edildi** (bkz. `..\CLAUDE.md`). `config/settings/prod.py`, `Dockerfile`, `gunicorn.conf.py` üretim benzeri çalışma için hazır duruyor ama kullanılmıyor; DigitalOcean/Sentry dosyaları kaldırıldı. `docker compose up --build` açılışta migrate + `seed_questions` (veritabanı boşsa) çalıştırır.

## Durum
Faz 0–3 tamam, frontend Faz 4–6 ile bağlandı. Sorular insan kontrolü bekliyor. Mobil uygulama iptal edildi; proje tamamlandı (isteğe bağlı: E2E, erişilebilirlik). Django Admin kaldırıldı (kullanıcı isteği); `auth`/`contenttypes` DRF için duruyor.
