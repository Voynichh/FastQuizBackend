# Fast Quiz — Proje Dokümanı

Oct 17, 2026 · @Someone

> **Kapsam notu:** Bu doküman başlangıç planıdır. Canlıya alma (Bölüm 11'deki DigitalOcean dağıtımı, `.do/app.yaml`, Sentry, staging) **kapsam dışı bırakıldı**; proje yerelde çalışan bir portföy projesidir. Güncel kararlar repoların `CLAUDE.md` dosyalarındadır.

## 1. Proje Özeti

Fast Quiz, her sorunun yalnızca 5 saniyede cevaplanabildiği, üyeliksiz ve hızlı oynanan bir bilgi yarışması uygulamasıdır. Kullanıcı bir kategori seçer, 20 soruyu tek tek cevaplar, sonunda puanını görür, adını girer ve en iyi 10 skorun yer aldığı skor tablosuna bakar.

| Konu | Karar |
| --- | --- |
| Uygulama adı | Fast Quiz |
| Hedef kitle | Gençler ve genç yetişkinler (16–30 yaş) |
| Kategoriler | Yazılım, Bilgisayar Mühendisliği, Yapay Zeka, Ülkeler, Fizik (5 adet) |
| Oturum başına soru | 20 (kategori içinden) |
| Soru başına süre | 5 saniye |
| Üyelik | Yok — sadece quiz sonunda isim alınır |
| Skor tablosu | En yüksek 10 puan |
| Platformlar | Web (Vue.js) şimdi, mobil (Vue.js + Capacitor, iOS ve Android) sonraki faz — aynı kod ve aynı API |
| Backend | Python + Django + Django REST Framework |
| Veritabanı | PostgreSQL |
| Repo yapısı | Backend ve frontend ayrı repolarda |

Başarı ölçütü: bir kullanıcı uygulamayı açtıktan sonra 3 tıklamada quize başlayabilmeli ve bir quiz turu yaklaşık 2 dakikada bitmelidir (20 soru × en fazla 5 sn + geçişler).

## 2. Kapsam ve Oyun Akışı

Kullanıcı bir quiz turunda bir soruyu cevaplamadan veya süresi dolmadan bir sonrakini göremez; geri dönmek de mümkün değildir.

### Oyun akışı

1. **Ana ekran:** Uygulama logosu, kısa açıklama, "Başla" butonu ve skor tablosuna bağlantı.
2. **Kategori seçimi:** 5 kategori kart olarak gösterilir. Kart seçilince sunucuda yeni bir quiz oturumu açılır.
3. **Geri sayım:** "3-2-1" animasyonu ile kullanıcı hazırlanır.
4. **Soru ekranı (20 kez tekrarlanır):**
   1. Soru metni ve 4 şık gösterilir, 5 saniyelik sayaç başlar.
   2. Kullanıcı bir şık seçer → cevap kilitlenir, doğru/yanlış geri bildirimi \~0,8 sn gösterilir.
   3. Süre dolarsa soru "boş" sayılır ve otomatik olarak sonraki soruya geçilir.
5. **Sonuç ekranı:** Toplam puan, doğru/yanlış/boş sayısı, ortalama cevap süresi.
6. **İsim girişi:** Kullanıcı takma adını yazar (2–20 karakter) ve skorunu kaydeder. İsterse kaydetmeden çıkabilir.
7. **Skor tablosu:** Seçilen kategori için ilk 10 skor gösterilir; kullanıcının skoru listedeyse vurgulanır.

### Oyun kuralları

| Kural | Değer |
| --- | --- |
| Soru sayısı | 20 (kategorideki havuzdan rastgele seçilir) |
| Şık sayısı | 4, tek doğru cevap |
| Süre | Soru başına 5 sn (sunucu tarafında doğrulanır) |
| Doğru cevap | 100 taban puan + hız bonusu (bkz. Bölüm 7) |
| Yanlış cevap | 0 puan |
| Süre aşımı / boş | 0 puan |
| Geri dönme / atlama | Yok |
| Şık sırası | Her oturumda karıştırılır |

### Kapsam içi (v1)

- 5 kategori, her kategori için en az 40 soruluk havuz (20 soru rastgele seçildiği için tekrar oynanabilirlik sağlar)
- Quiz oturumu, cevap kaydı, puan hesaplama
- Kategori bazlı ve genel skor tablosu (ilk 10)
- Django Admin üzerinden soru/kategori yönetimi
- Mobil uygulamaya hazır, versiyonlu REST API

### Kapsam dışı (v1)

- Kayıt olma, giriş yapma, şifre, profil
- Çok oyunculu / canlı yarışma modu
- Soru ekleme önerisi gibi kullanıcı içerikleri
- Çoklu dil (arayüz Türkçe; i18n altyapısı hazır tutulur)

## 3. Teknoloji Yığını ve Repo Yapısı

İki bağımsız repo olacak: `fast-quiz-backend` (Django REST API) ve `fast-quiz-frontend` (Vue 3 SPA). Mobil uygulama ayrı repo gerektirmez: aynı Vue kodu Capacitor ile iOS ve Android'e paketlenir ve aynı API'ye bağlanır.

| Katman | Teknoloji | Sürüm | Not |
| --- | --- | --- | --- |
| Dil (backend) | Python | 3.14.x | Django 6.1'in resmi olarak desteklediği en yeni sürüm. 9 Ekim 2026'da çıkan 3.15'e, Django resmi desteği ekleyince geçilir |
| Web framework | Django | 6.1.x | En güncel kararlı sürüm; Admin paneli soru yönetimi için kullanılır |
| API | Django REST Framework | 3.18.x | JSON, versiyonlu (`/api/v1/`); Django 6.1 ve Python 3.14/3.15 destekli |
| API dokümantasyonu | drf-spectacular | güncel | OpenAPI 3 şeması + Swagger UI; mobil ekip için tek kaynak |
| Veritabanı | PostgreSQL | 18.x | En güncel kararlı sürüm. PostgreSQL 19 şu an RC aşamasında, genel yayın 19 Kasım 2026'da planlanıyor |
| DB sürücüsü | psycopg | 3.x (güncel) | `psycopg[binary,pool]` |
| CORS | django-cors-headers | güncel | Web origin'leri beyaz listede |
| Rate limit | DRF throttling (+ Redis opsiyonel) | — | Skor spam'ını engeller |
| Ortam değişkenleri | django-environ | güncel | `.env` dosyası |
| Test (backend) | pytest, pytest-django, factory\_boy | güncel |  |
| Çalışma ortamı (frontend) | Node.js | 26 | 28 Ekim 2026'da LTS'e geçiyor; proje süresince desteklenen sürüm |
| Dil (frontend) | TypeScript | 6.x | Vue tip kontrolü (`vue-tsc`, Vue - Official eklentisi) henüz TypeScript 7'yi desteklemiyor; 7.1 + Volar desteği gelince 7'ye geçilir |
| UI framework | Vue | 3.5.x | Composition API, `<script setup>`. 3.6 (Vapor Mode) şu an RC; kararlı çıkınca değerlendirilir |
| Build aracı | Vite | 8.x | Rolldown tabanlı, en güncel ana sürüm |
| Router | Vue Router | 5.x |  |
| State | Pinia | 3.x | Quiz oturumu durumu |
| HTTP | Axios | güncel | Tek bir API istemcisi modülü |
| Stil | Tailwind CSS | 4.3.x | CSS tabanlı yapılandırma (`@theme`); tema renkleri tek yerden |
| Animasyon | Vue `<Transition>` + CSS | — | Ek kütüphane gerekmez |
| Test (frontend) | Vitest 4, Vue Test Utils, Playwright | güncel |  |
| Kod kalitesi | Ruff (lint + format), ESLint (flat config) + Prettier | güncel | pre-commit kancaları |
| Konteyner | Docker + docker-compose | `postgres:18`, `python:3.14-slim` | Aynı imaj yerelde ve DigitalOcean App Platform'da; üretimde Gunicorn + WhiteNoise |

**Sürüm politikası:** Her paket kurulumda en son kararlı yama sürümüyle sabitlenir (`requirements/*.txt`, `package-lock.json`); Dependabot ile aylık güncellenir. Ana sürüm geçişleri (Python 3.15, PostgreSQL 19, TypeScript 7, Vue 3.6) ilgili bağımlılıklar resmi destek verdiğinde ayrı bir PR ile yapılır.

Kaynaklar: [Python sürümleri](https://www.python.org/downloads/) · [Django 6.1 sürüm notları](https://docs.djangoproject.com/en/6.1/releases/6.1/) · [DRF sürüm notları](https://www.django-rest-framework.org/community/release-notes/) · [PostgreSQL 19 RC 1](https://www.postgresql.org/about/news/postgresql-19-rc-1-released-3409/) · [Node.js sürüm takvimi](https://nodejs.org/en/blog/announcements/evolving-the-nodejs-release-schedule) · [Vue sürümleri](https://endoflife.date/vue) · [Vite 8.1](https://vite.dev/blog/announcing-vite8-1) · [Vue ve TypeScript 7](https://tiagogalvao.com/typescript-7-vue-support/)

### Backend repo yapısı

```
fast-quiz-backend/
├── config/                 # settings (base, dev, prod), urls, wsgi/asgi
├── apps/
│   ├── quiz/               # Category, Question, Choice, QuizSession, Answer
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py     # puanlama ve süre doğrulama iş mantığı
│   │   ├── admin.py
│   │   └── tests/
│   └── leaderboard/        # ScoreEntry, top-10 sorguları
├── fixtures/               # başlangıç soru setleri (JSON)
├── requirements/           # base.txt, dev.txt, prod.txt
├── .do/
│   └── app.yaml            # DigitalOcean App Platform tanımı
├── docker-compose.yml      # sadece yerel geliştirme
├── Dockerfile              # yerel + App Platform için tek imaj
├── .dockerignore
├── gunicorn.conf.py
├── .env.example
└── README.md
```

### Frontend repo yapısı

```
fast-quiz-frontend/
├── src/
│   ├── api/                # axios istemcisi + uç nokta fonksiyonları
│   ├── assets/
│   ├── components/         # CategoryCard, TimerRing, ChoiceButton, ScoreTable...
│   ├── composables/        # useCountdown, useQuizSession
│   ├── stores/             # Pinia: quiz.ts
│   ├── views/              # Home, Categories, Quiz, Result, Leaderboard
│   ├── router/
│   ├── styles/             # tema tokenları (CSS değişkenleri)
│   └── types/              # API tipleri (OpenAPI şemasından üretilebilir)
├── tests/
├── .env.example            # VITE_API_BASE_URL
├── .do/
│   └── app.yaml            # DigitalOcean statik site tanımı
├── capacitor.config.ts     # mobil (iOS/Android) yapılandırması
├── ios/                    # Capacitor iOS projesi
├── android/                # Capacitor Android projesi
├── vite.config.ts
└── README.md
```

## 4. Sistem Mimarisi

Web ve mobil istemciler aynı Django REST API'ye bağlanır; API tek doğruluk kaynağıdır ve süre, puan, sıralama gibi tüm kurallar orada uygulanır.

&#91;embedded content: Sistem mimarisi · 2 istemci, 1 API, 1 veritabanı\]

İstemciler sadece ekranı çizer ve kullanıcının seçimini gönderir. Mobil uygulama eklendiğinde backend kodunda değişiklik gerekmez; sadece CORS listesine Capacitor origin'leri eklenir ve `X-Client` değeri farklıdır.

## 5. Veri Modeli (PostgreSQL)

Altı tablo yeterli: içerik için `Category`, `Question`, `Choice`; oyun için `QuizSession`, `SessionQuestion`; skor tablosu için `ScoreEntry`. Doğru cevap bilgisi hiçbir zaman soru gönderilirken istemciye verilmez.

### Category

| Alan | Tip | Not |
| --- | --- | --- |
| id | bigint PK |  |
| slug | varchar(50), unique | `yazilim`, `bilgisayar-muhendisligi`, `yapay-zeka`, `ulkeler`, `fizik` |
| name | varchar(100) | Ekranda görünen ad |
| description | text | Kart üzerindeki kısa açıklama |
| icon | varchar(50) | İkon adı (web ve mobil aynı ikon setini kullanır) |
| color | varchar(20) | Tema token adı, ör. `accent-violet` |
| order | smallint | Listeleme sırası |
| is\_active | boolean |  |

### Question

| Alan | Tip | Not |
| --- | --- | --- |
| id | bigint PK |  |
| category\_id | FK → Category | index |
| text | varchar(300) | 5 sn'de okunabilmesi için kısa tutulur |
| difficulty | smallint | 1 kolay, 2 orta, 3 zor |
| explanation | text, null | Sonuç ekranında gösterilebilir (opsiyonel) |
| is\_active | boolean | Pasif sorular havuzdan çıkar |
| created\_at / updated\_at | timestamptz |  |

### Choice

| Alan | Tip | Not |
| --- | --- | --- |
| id | bigint PK |  |
| question\_id | FK → Question |  |
| text | varchar(120) |  |
| is\_correct | boolean | Kısmi unique index: soru başına tek doğru şık |

### QuizSession

| Alan | Tip | Not |
| --- | --- | --- |
| id | uuid PK | İstemciye verilen oturum kimliği |
| token\_hash | varchar(64) | İstemciye bir kez verilen gizli anahtarın SHA-256 özeti |
| category\_id | FK → Category |  |
| status | varchar(12) | `active`, `completed`, `abandoned` |
| client\_type | varchar(10) | `web`, `ios`, `android` |
| current\_index | smallint | Sıradaki soru (0–19) |
| total\_score / correct\_count / wrong\_count / empty\_count | int | Bitince doldurulur |
| started\_at / finished\_at | timestamptz |  |

### SessionQuestion

| Alan | Tip | Not |
| --- | --- | --- |
| id | bigint PK |  |
| session\_id | FK → QuizSession | unique(session\_id, position) |
| question\_id | FK → Question | unique(session\_id, question\_id) |
| position | smallint | 0–19 |
| choice\_order | jsonb | Karıştırılmış şık id sırası |
| served\_at | timestamptz, null | Soru istemciye gönderildiği an (süre bunun üzerinden hesaplanır) |
| answered\_at | timestamptz, null |  |
| selected\_choice\_id | FK → Choice, null | Boş/süre aşımında null |
| result | varchar(10), null | `correct`, `wrong`, `timeout` |
| response\_ms | int, null | Sunucunun ölçtüğü süre |
| points | int |  |

### ScoreEntry (skor tablosu)

| Alan | Tip | Not |
| --- | --- | --- |
| id | bigint PK |  |
| session\_id | FK → QuizSession, unique | Bir oturum = en fazla bir skor kaydı |
| category\_id | FK → Category |  |
| player\_name | varchar(20) | Temizlenmiş ve küfür filtresinden geçmiş |
| score | int |  |
| correct\_count | smallint |  |
| avg\_response\_ms | int | Eşitlikte belirleyici |
| created\_at | timestamptz |  |

**İndeksler:** `ScoreEntry (category_id, score DESC, avg_response_ms ASC, created_at ASC)` ve genel liste için `(score DESC, avg_response_ms ASC, created_at ASC)`. Top 10 sorgusu bu indeksten doğrudan okunur.

**Sıralama kuralı:** Önce puan (yüksek), eşitlikte ortalama cevap süresi (düşük), o da eşitse önce kaydeden üstte.

## 6. API Tasarımı

API, web ve mobil istemcilerin aynı şekilde kullanabileceği durumsuz (stateless) bir JSON REST API'dir: çerez ve CSRF yerine oturum başına verilen bir token header'ı kullanılır, tüm yollar `/api/v1/` ile başlar.

### Mobil uyumluluk ilkeleri

- **Çerez yok:** Oturum kimliği `X-Session-Token` header'ı ile taşınır; mobil ve web aynı yöntemi kullanır.
- **Versiyonlama:** URL tabanlı (`/api/v1/`). Kırıcı değişiklikler `/api/v2/` ile gelir; v1 en az 6 ay desteklenir (mağaza güncellemesi yapmayan kullanıcılar için).
- **Zaman formatı:** Tüm zamanlar ISO 8601, UTC. Süreler milisaniye (`*_ms`).
- **Tek hata formatı:** Her hata aynı JSON gövdesiyle döner (aşağıda).
- **OpenAPI şeması:** `/api/v1/schema/` + `/api/v1/docs/` (Swagger). Web ve mobil tipler bu şemadan üretilebilir.
- **İstemci bilgisi:** İstemciler `X-Client: web|ios|android` ve `X-Client-Version` gönderir; ileride minimum sürüm zorlaması için kullanılır.
- **Medya:** Görsel gerekirse mutlak URL döner (mobilde göreli yol sorun çıkarır).

### Uç noktalar

| Metot | Yol | Açıklama | Token |
| --- | --- | --- | --- |
| GET | `/api/v1/categories/` | Aktif kategoriler + soru sayısı | Hayır |
| POST | `/api/v1/sessions/` | Kategori için yeni quiz oturumu açar, 20 soruyu seçer | Hayır |
| GET | `/api/v1/sessions/{id}/current/` | Sıradaki soruyu verir ve süreyi başlatır | Evet |
| POST | `/api/v1/sessions/{id}/answers/` | Aktif soruya cevap gönderir | Evet |
| GET | `/api/v1/sessions/{id}/result/` | Oturum özeti ve tahmini sıralama | Evet |
| POST | `/api/v1/sessions/{id}/score/` | İsmi alır, skoru tabloya kaydeder | Evet |
| GET | `/api/v1/leaderboard/?category={slug}` | İlk 10 skor (kategori yoksa genel) | Hayır |
| GET | `/api/v1/health/` | Sağlık kontrolü (deploy ve izleme) | Hayır |

### Örnek: oturum açma

```
POST /api/v1/sessions/
{ "category": "yapay-zeka" }

201 Created
{
  "session_id": "8f1c...",
  "session_token": "q7Xk...",      // sadece bu yanıtta döner, istemci saklar
  "category": { "slug": "yapay-zeka", "name": "Yapay Zeka" },
  "total_questions": 20,
  "time_limit_ms": 5000
}
```

### Örnek: sıradaki soru

```
GET /api/v1/sessions/8f1c.../current/
X-Session-Token: q7Xk...

200 OK
{
  "position": 3,                    // 0 tabanlı, ekranda 4/20
  "total_questions": 20,
  "question": {
    "id": 512,
    "text": "Transformer mimarisini tanıtan makalenin adı nedir?",
    "choices": [
      { "id": 2041, "text": "Attention Is All You Need" },
      { "id": 2043, "text": "Deep Residual Learning" },
      { "id": 2040, "text": "ImageNet Classification" },
      { "id": 2042, "text": "Generative Adversarial Nets" }
    ]
  },
  "time_limit_ms": 5000,
  "server_time": "2026-10-17T08:12:03.120Z",
  "deadline": "2026-10-17T08:12:08.120Z"
}
```

Aynı soru için tekrar istek gelirse (ör. sayfa yenileme) yeni süre başlatılmaz, aynı `deadline` döner. Süresi geçmiş bir soru varsa sunucu onu `timeout` olarak kapatır ve bir sonrakini verir. Tüm sorular bitmişse `409 session_completed` döner.

### Örnek: cevap gönderme

```
POST /api/v1/sessions/8f1c.../answers/
X-Session-Token: q7Xk...
{ "question_id": 512, "choice_id": 2041 }   // süre dolduysa choice_id: null

200 OK
{
  "result": "correct",              // correct | wrong | timeout
  "correct_choice_id": 2041,
  "points": 168,
  "response_ms": 1600,
  "total_score": 412,
  "is_last": false
}
```

### Örnek: skoru kaydetme

```
POST /api/v1/sessions/8f1c.../score/
X-Session-Token: q7Xk...
{ "player_name": "Ece" }

201 Created
{ "rank": 4, "in_top_10": true, "score": 2310 }
```

### Hata formatı

```
{
  "error": {
    "code": "answer_too_late",
    "message": "Bu soru için süre doldu.",
    "details": {}
  }
}
```

| HTTP | code | Ne zaman |
| --- | --- | --- |
| 400 | `validation_error` | Eksik/hatalı alan, geçersiz isim |
| 401 | `invalid_session_token` | Token yok veya eşleşmiyor |
| 404 | `not_found` | Oturum/kategori bulunamadı |
| 409 | `question_mismatch` | Gönderilen soru aktif soru değil |
| 409 | `already_answered` | Aynı soruya ikinci cevap |
| 409 | `session_completed` | Bitmiş oturuma soru/cevap isteği |
| 409 | `score_already_saved` | Aynı oturum için ikinci skor kaydı |
| 429 | `rate_limited` | İstek sınırı aşıldı |

## 7. Zamanlayıcı, Puanlama ve Hile Önleme

Süre ve puan tamamen sunucuda hesaplanır; istemcideki sayaç sadece görseldir. Böylece web veya mobil istemci değiştirilse bile 5 saniye kuralı ve puanlar güvenilir kalır.

### Puan formülü

Doğru cevap 100 taban puan + kalan süreye orantılı en fazla 100 hız bonusu getirir. Bir soru en fazla 200, bir quiz en fazla 4.000 puan eder.

```latex
\text{puan} = \begin{cases} 100 + \operatorname{round}\left(100 \cdot \dfrac{5000 - t_{ms}}{5000}\right) & \text{doğru} \\ 0 & \text{yanlış veya süre aşımı} \end{cases}
```

Örnek: 1,6 sn'de doğru cevap → 100 + 68 = 168 puan. 4,9 sn'de doğru cevap → 102 puan.

### Süre ölçümü

1. İstemci `GET /current/` çağırdığında sunucu `served_at` zamanını kaydeder ve `deadline = served_at + 5000 ms` döner.
2. Cevap geldiğinde sunucu `response_ms = answered_at − served_at` hesaplar.
3. **Ağ toleransı:** `response_ms ≤ 5500` olan cevaplar kabul edilir (500 ms ağ gecikmesi payı). Bonus hesabında süre en fazla 5000 ms alınır.
4. `response_ms > 5500` ise cevap `timeout` sayılır ve 0 puan verilir.
5. İstemci sayacı, sunucu saat farkını düzeltmek için `server_time` ile kendi saatini karşılaştırır: `yerel_bitiş = şimdi + (deadline − server_time)`.
6. Süre dolunca istemci `choice_id: null` gönderir; göndermezse bir sonraki `GET /current/` çağrısında sunucu soruyu kendisi `timeout` olarak kapatır.

### Hile önleme kuralları

- Doğru şık bilgisi soru gönderilirken asla yanıtta yer almaz; sadece cevap sonrasında döner.
- Sorular tek tek verilir: aktif soru cevaplanmadan veya süresi dolmadan sonraki soru API'den alınamaz.
- Her soruya tek cevap: ikinci cevap `409 already_answered` döner. Bunun için cevap kaydı `SELECT … FOR UPDATE` ile kilitlenen transaction içinde yapılır.
- Puan istemciden alınmaz; skor kaydında sadece `player_name` gönderilir, puan oturumdan okunur.
- Skor sadece `completed` durumundaki oturum için ve bir kez kaydedilebilir.
- Oturum token'ı tahmin edilemez (`secrets.token_urlsafe(32)`), veritabanında sadece özeti tutulur.
- 10 dakika işlem görmeyen oturum `abandoned` olur ve skor kaydı alamaz.
- Rate limit: IP başına dakikada 10 oturum açma, 60 cevap, 5 skor kaydı.
- İsim filtresi: baş/son boşluk temizlenir, 2–20 karakter, harf/rakam/boşluk/`_-.` dışındaki karakterler reddedilir, Türkçe ve İngilizce küfür listesinden kontrol edilir.
- Sekme değiştirme veya uygulamayı arka plana alma süreyi durdurmaz (süre sunucuda işler).

## 8. Frontend (Vue 3)

Frontend, mobil öncelikli (mobile-first) tasarlanmış bir tek sayfa uygulamasıdır; tüm iş mantığı backend'de olduğu için Vue tarafı ekranları, sayacı ve geçiş animasyonlarını yönetir.

### Ekranlar ve yollar

| Yol | Ekran | İçerik |
| --- | --- | --- |
| `/` | Ana sayfa | Logo, slogan, "Başla" butonu, skor tablosu bağlantısı |
| `/kategoriler` | Kategori seçimi | 5 kategori kartı (ikon, renk, kısa açıklama) |
| `/quiz/:sessionId` | Soru ekranı | İlerleme çubuğu (4/20), dairesel 5 sn sayacı, soru, 4 şık, anlık puan |
| `/sonuc/:sessionId` | Sonuç + isim girişi | Puan animasyonu, doğru/yanlış/boş, ortalama süre, isim formu |
| `/skor-tablosu` | Skor tablosu | Kategori sekmeleri + genel; ilk 10, kullanıcının satırı vurgulu |
| `*` | 404 | Ana sayfaya dönüş |

### Bileşenler

- `CategoryCard` — kategori kartı, hover/tıklamada hafif büyüme
- `CountdownOverlay` — quiz öncesi 3-2-1
- `TimerRing` — SVG dairesel sayaç; son 2 saniyede renk uyarı tonuna geçer
- `ProgressBar` — 20 segmentli ilerleme; doğru/yanlış/boş renkli
- `ChoiceButton` — durumlar: varsayılan, seçili, doğru, yanlış, devre dışı
- `ScoreCounter` — sonuç ekranında sayarak artan puan
- `NameForm` — isim girişi, anlık doğrulama
- `LeaderboardTable` — sıra, isim, puan, doğru sayısı; ilk 3 için madalya rozeti

### State yönetimi (Pinia `quiz` store)

- `sessionId`, `sessionToken`, `category`, `position`, `currentQuestion`, `deadline`, `totalScore`, `answers[]`, `status`
- `sessionId` ve `sessionToken` `sessionStorage`'da tutulur; sayfa yenilenirse `GET /current/` ile kalınan yerden devam edilir (süre sunucuda işlemeye devam ettiği için avantaj sağlamaz).
- Aksiyonlar: `startSession(slug)`, `loadCurrent()`, `submitAnswer(choiceId | null)`, `saveScore(name)`, `reset()`

### Composable'lar

- `useCountdown(deadline, serverTime)` — `requestAnimationFrame` ile akıcı sayaç, süre dolunca `onExpire` çağırır
- `useQuizSession()` — store ve API çağrılarını ekranlara bağlar, çift tıklamayı engeller

### Davranış detayları

- Bir şık seçilince tüm şıklar kilitlenir, istek tamamlanınca doğru şık yeşil, yanlış seçim kırmızı gösterilir, \~800 ms sonra sonraki soru yüklenir.
- Soru geçişlerinde kayan/solma animasyonu (≤ 250 ms) kullanılır; sayaç yeni soru ekranda göründüğünde başlar.
- Klavye desteği: `1–4` veya `A–D` tuşlarıyla şık seçimi.
- Ağ hatasında tek otomatik yeniden deneme, sonra "Bağlantı sorunu" bildirimi.
- Ses efektleri (doğru/yanlış/tik-tak) opsiyonel ve varsayılan kapalı; ayar `localStorage`'da tutulur.

### Mobil uygulama (Vue.js + Capacitor)

Mobil uygulama da Vue.js ile yazılır: web uygulamasının aynı Vue 3 kodu Capacitor ile yerel (native) iOS ve Android uygulamasına paketlenir. Ayrı bir repo gerekmez; `fast-quiz-frontend` reposuna `ios/` ve `android/` klasörleri eklenir, ekranlar, store ve API istemcisi ortak kalır.

| Konu | Seçim | Not |
| --- | --- | --- |
| Paketleme | Capacitor 8.5.x | En güncel kararlı sürüm; 9.0 alfa aşamasında |
| Titreşim | `@capacitor/haptics` | Doğru/yanlış cevapta kısa titreşim |
| Yerel ayar saklama | `@capacitor/preferences` | Ses ayarı ve devam eden oturum bilgisi |
| Uygulama yaşam döngüsü | `@capacitor/app` | Android geri tuşu, arka plana geçme |
| Durum çubuğu / açılış ekranı | `@capacitor/status-bar`, `@capacitor/splash-screen` | Koyu temaya uygun renkler |
| İkon ve açılış görselleri | `@capacitor/assets` | Tek kaynak görselden tüm boyutlar |

**Platforma özel davranışlar**

- `X-Client` header'ı `Capacitor.getPlatform()` ile `web`, `ios` veya `android` olarak gönderilir.
- Oturum bilgisi web'de `sessionStorage`, mobilde `Preferences` ile tutulur; bunu tek bir `storage` modülü soyutlar.
- Quiz sırasında Android geri tuşu veya uygulamayı arka plana alma süreyi durdurmaz (süre sunucuda işler); geri tuşunda "Quizden çıkılsın mı?" onayı gösterilir.
- Çentikli ekranlar için `env(safe-area-inset-*)` boşlukları kullanılır; isim girişinde klavye formu kapatmaz.
- API adresi derlemede mutlak URL olarak gömülür (`VITE_API_BASE_URL=https://api.fastquiz.app/api/v1`); mobil derleme `vite build --mode mobile` ile yapılır.

**Backend tarafı:** Capacitor uygulaması bir WebView içinde çalıştığı için istekleri CORS kurallarına tabidir. Varsayılan origin'ler iOS'ta `capacitor://localhost`, Android'de `https://localhost` olduğundan bu ikisi `CORS_ALLOWED_ORIGINS` listesine eklenir. Bunun dışında backend'de değişiklik gerekmez.

**Derleme ve yayın:** `npm run build && npx cap sync` ile web kodu yerel projelere kopyalanır. iOS derlemesi macOS'ta Xcode ile, Android derlemesi Android Studio ile yapılır; mağaza yayını için Apple Developer ve Google Play Console hesapları gerekir. Mobil sürümler mağazadan dağıtıldığı için API'nin `/api/v1/` sözleşmesi geriye uyumlu tutulur (Bölüm 6).

## 9. UI/UX Tasarım Rehberi

Tema: saf siyah yerine lacivert-mor tonlu "yumuşak koyu" bir zemin ve üzerinde orta doygunlukta canlı vurgu renkleri. Neon parlaklık, tam doygun renkler ve büyük renkli yüzeyler kullanılmaz; renk küçük alanlarda (kart kenarı, ikon, buton, sayaç) vurgu olarak çalışır.

### Renk paleti

| Token | Hex | Kullanım |
| --- | --- | --- |
| `--bg` | `#1E2034` | Sayfa zemini (siyah değil, koyu lacivert) |
| `--surface` | `#282B45` | Kartlar, soru kutusu |
| `--surface-raised` | `#33375A` | Şıklar, hover durumları, modal |
| `--border` | `#3F4468` | İnce kenarlıklar |
| `--text` | `#F2F3FA` | Ana metin |
| `--text-muted` | `#A9ADCB` | İkincil metin, etiketler |
| `--primary` | `#8B7CF6` | Ana buton, odak halkası, marka rengi (yumuşak mor) |
| `--primary-hover` | `#9D90F8` | Ana buton hover |
| `--success` | `#4ADE9A` | Doğru cevap |
| `--danger` | `#F27A7A` | Yanlış cevap |
| `--warning` | `#F5B84C` | Sayacın son 2 saniyesi |

### Kategori renkleri

| Kategori | Token | Hex | İkon önerisi |
| --- | --- | --- | --- |
| Yazılım | `--cat-software` | `#8B7CF6` | Kod parantezi `</>` |
| Bilgisayar Mühendisliği | `--cat-compeng` | `#5AB8F0` | İşlemci / devre |
| Yapay Zeka | `--cat-ai` | `#E57CD8` | Beyin / kıvılcım |
| Ülkeler | `--cat-countries` | `#3FD0B4` | Dünya |
| Fizik | `--cat-physics` | `#F5B84C` | Atom |

Kategori rengi o kategorideki quiz boyunca ilerleme çubuğu, sayaç halkası ve kart kenarında tekrar edilir; kullanıcı hangi kategoride olduğunu renkten anlar.

### Tipografi

- Başlıklar: **Outfit** (600–700), yuvarlak ve genç bir görünüm
- Metin ve şıklar: **Inter** (400–500)
- Ölçek: soru 22–26 px (mobilde 20 px), şıklar 17 px, etiketler 13 px
- Sayılar (puan, sayaç): `font-variant-numeric: tabular-nums` ile titreşimsiz

### Bileşen stili

- Köşe yarıçapı: kartlar 20 px, butonlar ve şıklar 14 px
- Gölge yerine hafif kenarlık + çok düşük opaklıkta renkli parlama (`box-shadow: 0 0 0 1px` + `0 8px 24px` %15 opaklık)
- Arka planda çok soluk, büyük ve bulanık iki renk lekesi (mor + turkuaz, %10 opaklık) ile derinlik hissi
- Şık butonları: tam genişlik, en az 56 px yükseklik (mobilde başparmak dostu), solda A/B/C/D rozeti
- Sayaç: soru kartının üstünde dairesel halka, ortasında kalan saniye; son 2 sn'de `--warning` rengine geçer ve hafifçe nabız atar

### Hareket

- Geçişler 150–250 ms, `ease-out`; abartılı zıplama yok
- Doğru cevapta kısa yeşil parlama, yanlışta hafif yatay sallanma (≤ 200 ms)
- Sonuç ekranında puan sayarak artar; ilk 10'a girerse küçük konfeti efekti
- `prefers-reduced-motion` açıksa tüm animasyonlar sadece solmaya indirgenir

### Erişilebilirlik

- Metin/zemin kontrastı en az WCAG AA (4,5:1); `--text` ve `--text-muted` bu oranı `--bg` üzerinde sağlar
- Doğru/yanlış sadece renkle değil, ikonla da (✓ / ✕) gösterilir
- Tüm butonlarda görünür odak halkası (`--primary`)
- Mobilde minimum dokunma alanı 44 × 44 px

## 10. Güvenlik, Test ve Kalite

Kullanıcı hesabı olmadığı için saldırı yüzeyi küçüktür; asıl riskler sahte skor gönderimi, skor tablosuna uygunsuz isim yazılması ve API'nin istekle boğulmasıdır.

### Güvenlik

- `DEBUG=False`, `SECRET_KEY` ve veritabanı bilgileri sadece ortam değişkeninden okunur; `.env` repoya girmez.
- `ALLOWED_HOSTS` ve `CORS_ALLOWED_ORIGINS` sadece bilinen domainleri içerir (Capacitor mobil uygulaması da WebView'de çalıştığı için iOS capacitor://localhost ve Android https://localhost origin'leri listeye eklenir; kimlik doğrulama çerezle değil oturum token'ıyla yapıldığından bu güvenli kalır).
- HTTPS zorunlu; `SECURE_SSL_REDIRECT`, HSTS ve güvenli header'lar açık.
- Django Admin farklı bir yolda (`/yonetim/` gibi), güçlü şifre ve sadece yetkili personel.
- Tüm sorgular ORM ile; ham SQL yok. İsimler Vue tarafında metin olarak basılır (`v-html` yasak).
- Bölüm 7'deki rate limit ve isim filtresi kuralları.
- Bağımlılıklar için Dependabot veya `pip-audit` / `npm audit` CI'da çalışır.

### Test stratejisi

| Katman | Araç | Kapsam | Hedef |
| --- | --- | --- | --- |
| Backend birim | pytest | Puan formülü, süre toleransı, isim filtresi, sıralama kuralı | %90+ kapsama (`services.py`) |
| Backend API | pytest + DRF APIClient | Tüm uç noktalar, hata kodları, çift cevap, süresi geçmiş cevap, token kontrolü | Her uç nokta için başarı + hata senaryosu |
| Backend eşzamanlılık | pytest (transaction testleri) | Aynı soruya eşzamanlı iki cevap → tek kayıt |  |
| Frontend birim | Vitest + Vue Test Utils | `useCountdown`, store aksiyonları, `ChoiceButton` durumları |  |
| E2E | Playwright | Kategori seç → 20 soru → isim gir → skor tablosunda gör; süre aşımı akışı | Ana akış her PR'da |

Süreye bağlı testlerde gerçek bekleme yerine saat dondurma kullanılır (`freezegun` / `time-machine` backend'de, `vi.useFakeTimers()` frontend'de).

### CI

Her iki repoda GitHub Actions: lint → test → build. Backend pipeline'ı PostgreSQL servis konteyneriyle çalışır (SQLite ile test edilmez, çünkü kısmi index ve `FOR UPDATE` davranışı farklıdır). Backend CI ayrıca Docker imajını build eder ve doctl apps spec validate ile app spec dosyasını doğrular. Testler geçip main dalına merge edilince App Platform otomatik deploy eder.

## 11. Kurulum, Ortamlar ve Dağıtım

Yerelde backend ve PostgreSQL docker-compose ile, frontend Vite geliştirme sunucusuyla çalışır; üç ortam vardır: development, staging, production. Staging ve production DigitalOcean App Platform'da çalışır: backend Dockerfile ile servis, frontend statik site olarak.

### Yerel kurulum

Önkoşullar: Python 3.14, Node.js 26, Docker (PostgreSQL 18 compose ile gelir).

```
# backend
git clone <repo>/fast-quiz-backend && cd fast-quiz-backend
cp .env.example .env
docker compose up -d db
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py loaddata fixtures/categories.json fixtures/questions_*.json
python manage.py createsuperuser
python manage.py runserver        # http://localhost:8000/api/v1/docs/

# frontend
git clone <repo>/fast-quiz-frontend && cd fast-quiz-frontend
cp .env.example .env               # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm install
npm run dev                        # http://localhost:5173
```

### Ortam değişkenleri (backend)

| Değişken | Örnek | Açıklama |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | dev / prod ayarları |
| `SECRET_KEY` | — | Üretimde uzun, rastgele |
| `DATABASE_URL` | `postgres://quiz:quiz@localhost:5432/fastquiz` | PostgreSQL bağlantısı |
| `ALLOWED_HOSTS` | `api.fastquiz.app` |  |
| `CORS_ALLOWED_ORIGINS` | `https://fastquiz.app`,capacitor://localhost,https://localhost | Web frontend origin'i |
| `QUIZ_QUESTION_COUNT` | `20` | Oturum başına soru |
| `QUIZ_TIME_LIMIT_MS` | `5000` | Soru süresi |
| `QUIZ_GRACE_MS` | `500` | Ağ toleransı |
| `LEADERBOARD_SIZE` | `10` | Skor tablosu uzunluğu |

Oyun parametreleri ortam değişkeninde tutulur ve API yanıtlarında (`time_limit_ms`, `total_questions`) döndürülür; böylece web ve mobil istemciler bu değerleri koda gömmez.

### Dağıtım: DigitalOcean App Platform

İki repo, DigitalOcean App Platform'da iki ayrı uygulama olarak yayınlanır: backend Dockerfile'dan imajı oluşturulan bir **servis** (web service), frontend ise derlenip CDN üzerinden sunulan bir **statik site**. Veritabanı DigitalOcean Managed PostgreSQL 18 kümesidir; tüm kaynaklar Türkiye'ye en yakın bölge olan Frankfurt'ta (`fra` / `fra1`) açılır.

| Bileşen | DigitalOcean kaynağı | Kaynak repo | Domain |
| --- | --- | --- | --- |
| Backend API | App Platform → Service (Dockerfile) | `fast-quiz-backend` | `api.fastquiz.app` |
| Migration | App Platform → Job (`PRE_DEPLOY`) | `fast-quiz-backend` | — |
| Veritabanı | Managed PostgreSQL 18 (Standard) | — | Özel ağ, sadece uygulama erişebilir |
| Frontend | App Platform → Static Site | `fast-quiz-frontend` | `fastquiz.app` |
| İzleme | App Platform Insights + Sentry | — | — |

Backend ve frontend ayrı uygulama olduğu için birbirinden bağımsız deploy edilir; mobil uygulama da doğrudan `api.fastquiz.app` adresini kullanır.

### Backend Docker dosyaları

Aynı Dockerfile hem yerel geliştirmede (docker-compose) hem App Platform'da kullanılır. İmaj çok aşamalıdır (multi-stage), root olmayan kullanıcıyla çalışır ve statik dosyaları build sırasında toplar.

**`Dockerfile`**

```
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
RUN SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]
```

`psycopg[binary]` kullanıldığı için imaja derleyici veya `libpq-dev` kurmaya gerek yoktur.

**`gunicorn.conf.py`**

```
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
worker_class = "gthread"
timeout = 30
graceful_timeout = 20
accesslog = "-"          # loglar stdout'a; App Platform toplar
errorlog = "-"
forwarded_allow_ips = "*"  # TLS, App Platform'un önündeki yük dengeleyicide sonlanır
```

**`.dockerignore`**

```
.git
.github
.venv
__pycache__/
*.pyc
.env
.env.*
!.env.example
.pytest_cache/
.ruff_cache/
htmlcov/
staticfiles/
docs/
```

**`docker-compose.yml`** (sadece yerel geliştirme)

```
services:
  db:
    image: postgres:18
    environment:
      POSTGRES_DB: fastquiz
      POSTGRES_USER: quiz
      POSTGRES_PASSWORD: quiz
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql   # PostgreSQL 18 imajının veri dizini
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U quiz -d fastquiz"]
      interval: 5s
      retries: 10

  api:
    build:
      context: .
      args:
        REQUIREMENTS: dev
    env_file: .env
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.dev
      DATABASE_URL: postgres://quiz:quiz@db:5432/fastquiz
    command: python manage.py runserver 0.0.0.0:8000
    ports: ["8000:8000"]
    volumes:
      - .:/app
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

Yerelde `docker compose up` ile API ve veritabanı birlikte kalkar; testler `docker compose run --rm api pytest` ile çalışır. Üretim imajı App Platform'da `prod` bağımlılıklarıyla build edilir.

### Backend uygulama tanımı (`.do/app.yaml`)

Uygulama, repodaki app spec dosyasıyla tanımlanır; böylece altyapı da kodla birlikte versiyonlanır. `main` dalına her push'ta App Platform imajı build eder, önce migration job'ını çalıştırır, yeni instance sağlık kontrolünü geçince trafiği ona aktarır (kesintisiz deploy).

```
name: fast-quiz-api
region: fra

domains:
  - domain: api.fastquiz.app
    type: PRIMARY

# Tüm bileşenlerde (servis + job) geçerli ortam değişkenleri
envs:
  - key: DJANGO_SETTINGS_MODULE
    value: config.settings.prod
  - key: SECRET_KEY
    type: SECRET                 # değer panelden girilir, şifreli saklanır
  - key: DATABASE_URL
    scope: RUN_TIME
    value: ${db.DATABASE_URL}    # bağlı veritabanından otomatik gelir (sslmode=require)
  - key: ALLOWED_HOSTS
    value: api.fastquiz.app,${APP_DOMAIN}
  - key: CORS_ALLOWED_ORIGINS
    value: https://fastquiz.app,capacitor://localhost,https://localhost
  - key: CSRF_TRUSTED_ORIGINS
    value: https://api.fastquiz.app   # Django Admin girişi için
  - key: SENTRY_DSN
    type: SECRET

services:
  - name: api
    github:
      repo: <github-kullanici>/fast-quiz-backend
      branch: main
      deploy_on_push: true
    dockerfile_path: Dockerfile
    http_port: 8000
    instance_count: 1            # trafik artınca 2+
    instance_size_slug: <panelde-secilen-plan>
    health_check:
      http_path: /api/v1/health/
      initial_delay_seconds: 10
      period_seconds: 10
      timeout_seconds: 3
      failure_threshold: 3
    envs:
      - key: WEB_CONCURRENCY
        value: "2"

jobs:
  - name: migrate
    kind: PRE_DEPLOY             # her deploy öncesi; hata verirse deploy durur
    github:
      repo: <github-kullanici>/fast-quiz-backend
      branch: main
    dockerfile_path: Dockerfile
    instance_size_slug: <en-kucuk-plan>
    run_command: python manage.py migrate --noinput

databases:
  - name: db
    engine: PG
    version: "18"
    production: true             # önceden oluşturulmuş Managed PostgreSQL kümesi
    cluster_name: fast-quiz-db
    db_name: fastquiz
    db_user: fastquiz
```

Veritabanı uygulamaya bağlandığında DigitalOcean uygulamayı kümenin güvenilir kaynaklarına (trusted sources) ekler; küme internete açılmaz.

### Frontend uygulama tanımı (`.do/app.yaml`)

```
name: fast-quiz-web
region: fra

domains:
  - domain: fastquiz.app
    type: PRIMARY
  - domain: www.fastquiz.app
    type: ALIAS

static_sites:
  - name: web
    github:
      repo: <github-kullanici>/fast-quiz-frontend
      branch: main
      deploy_on_push: true
    environment_slug: node-js
    build_command: npm ci && npm run build   # vue-tsc + vite build
    output_dir: dist
    catchall_document: index.html            # Vue Router yolları yenilemede 404 vermez
    envs:
      - key: VITE_API_BASE_URL
        scope: BUILD_TIME                    # Vite değeri build sırasında koda gömer
        value: https://api.fastquiz.app/api/v1
```

Node sürümü `package.json` içindeki `"engines": { "node": "26.x" }` alanıyla seçilir. App Platform buildpack'i henüz 26'yı sunmuyorsa `24.x` (LTS) yazılır; uygulama kodu iki sürümde de aynı çalışır.

### Django üretim ayarları (`config/settings/prod.py`)

- **Proxy arkasında HTTPS:** TLS, App Platform'un önünde sonlanır. `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`, `SECURE_SSL_REDIRECT = True`, HSTS ve güvenli çerez ayarları açılır.
- **Sağlık kontrolü:** App Platform kontrol isteğini konteynere iç ağdan ve HTTP üzerinden gönderir; bu istek `ALLOWED_HOSTS` ve HTTPS yönlendirmesine takılabilir. Bu yüzden `/api/v1/health/` yolunu yanıtlayan küçük bir `HealthCheckMiddleware`, `MIDDLEWARE` listesinin **en başına** konur ve veritabanına basit bir `SELECT 1` atıp 200 döner.
- **Statik dosyalar:** WhiteNoise (`CompressedManifestStaticFilesStorage`); Admin paneli ve Swagger UI dosyaları imajın içinden sunulur, ayrı bir depolama gerekmez.
- **Veritabanı:** `DATABASE_URL` django-environ ile okunur; `OPTIONS: {"sslmode": "require", "pool": True}` ile psycopg bağlantı havuzu kullanılır.
- **Önbellek ve rate limit:** DRF throttling Django önbelleğini kullanır. Tek instance'ta varsayılan önbellek yeterlidir; 2+ instance'a çıkınca sayaçların paylaşılması için `DatabaseCache` veya DigitalOcean Managed Valkey kullanılır.
- **Loglama:** Tüm loglar stdout'a yazılır; App Platform'un log ekranında ve log yönlendirme (log forwarding) hedeflerinde görünür.
- **Gizli değerler:** `SECRET_KEY`, `SENTRY_DSN` gibi değerler sadece App Platform'da `SECRET` tipinde tutulur; repoda yalnızca `.env.example` bulunur.

### Deploy akışı

1. DigitalOcean'da Frankfurt (`fra1`) bölgesinde `fast-quiz-db` adıyla Managed PostgreSQL 18 kümesi oluşturulur; `fastquiz` veritabanı ve kullanıcısı açılır.
2. Backend: `doctl apps create --spec .do/app.yaml` ile uygulama oluşturulur, `SECRET_KEY` ve `SENTRY_DSN` panelden girilir.
3. İlk deploy sonrası tek seferlik komutlar App Platform konsolundan çalıştırılır: `python manage.py loaddata fixtures/categories.json fixtures/questions_*.json` ve `python manage.py createsuperuser`.
4. Frontend: aynı şekilde kendi reposundaki spec ile statik site uygulaması oluşturulur.
5. DNS: `fastquiz.app` ve `api.fastquiz.app` için App Platform'un verdiği kayıtlar domain sağlayıcısına eklenir; SSL sertifikaları otomatik üretilir ve yenilenir.
6. Sonraki her `main` push'u otomatik deploy olur. Spec değişikliği `doctl apps update <app-id> --spec .do/app.yaml` ile uygulanır; `doctl apps spec validate` CI'da çalıştırılır.
7. Staging: `develop` dalına bağlı `fast-quiz-api-staging` ve `fast-quiz-web-staging` uygulamaları açılır; staging ayrı bir veritabanı (aynı kümede ayrı DB veya küçük ayrı küme) kullanır.

**Geri alma:** App Platform'da önceki başarılı deploy tek tıkla geri yüklenebilir. Migration'lar geriye uyumlu yazılır (önce sütun ekle, sonraki sürümde eskisini kaldır) ki geri alma veritabanını bozmasın.

## 12. Geliştirme Yol Haritası ve Claude Code ile Çalışma

Backend önce yapılır, çünkü frontend ve mobil aynı API sözleşmesine dayanır; her faz tek başına çalışır ve test edilmiş halde biter.

### Fazlar

- [ ] **Faz 0 — Hazırlık:** İki repo, `CLAUDE.md` dosyaları, Dockerfile, docker-compose (PostgreSQL), .do/app.yaml dosyaları, lint/format ayarları, CI iskeleti
- [ ] **Faz 1 — Backend veri katmanı:** Modeller, migration'lar, Django Admin (soru + şıklar tek ekranda, inline), kategori fixture'ları
- [ ] **Faz 2 — Soru havuzu:** Kategori başına en az 40 soru (toplam 200+), JSON fixture olarak; doğruluk ve kısalık kontrolü
- [ ] **Faz 3 — Backend API:** `services.py` (oturum, süre, puan), uç noktalar, hata formatı, rate limit, OpenAPI şeması, testler
- [ ] **Faz 4 — Frontend iskelet ve tema:** Vite + Vue + TS, router, Pinia, Tailwind, tema tokenları, ana sayfa ve kategori ekranı
- [ ] **Faz 5 — Quiz akışı:** Geri sayım, soru ekranı, `TimerRing`, cevap geri bildirimi, sayfa yenilemeye dayanıklılık
- [ ] **Faz 6 — Sonuç ve skor tablosu:** Puan animasyonu, isim formu, skor tablosu, vurgulu satır
- [ ] **Faz 7 — Kalite ve yayın:** E2E testler, erişilebilirlik kontrolü, DigitalOcean App Platform'da staging → production deploy, Sentry
- [ ] **Faz 8 — Mobil uygulama:** Aynı `/api/v1/` ile; Vue.js + Capacitor ile iOS ve Android paketleri, mağaza yayınları (Bölüm 8)

### Claude Code ile çalışma önerileri

1. Bu dokümanı her iki repoya `docs/PROJECT.md` olarak koyun ve `CLAUDE.md` içinde ona referans verin.
2. `CLAUDE.md`'ye kalıcı kuralları yazın: kod stili, klasör yapısı, "puan ve süre sadece `services.py`'de hesaplanır", "doğru şık bilgisi soru yanıtına asla eklenmez", test komutları.
3. Her fazı ayrı oturumda ve ayrı PR/commit olarak isteyin; büyük işlerde önce plan modunda plan çıkartıp onaylayın.
4. Backend'de önce testleri yazdırın (puan formülü, süre toleransı, çift cevap), sonra uygulamayı.
5. Faz 3 bitince `/api/v1/schema/` çıktısını frontend reposuna kopyalayıp tipleri bu şemadan ürettirin; frontend'in API'yi tahmin etmesini engeller.
6. Soru havuzunu Claude ile üretebilirsiniz, ancak her soruyu bir insan kontrol etmeli: yanlış bilgi içeren soru, 5 saniyelik formatta kullanıcıyı en çok rahatsız eden hatadır.

### Örnek ilk komut (backend reposunda)

```
docs/PROJECT.md dosyasını oku. Faz 0 ve Faz 1'i uygula:
Django projesini config/ ve apps/quiz, apps/leaderboard yapısıyla kur,
Bölüm 5'teki modelleri ve kısıtları oluştur, Admin'i inline şıklarla ayarla,
docker-compose ile PostgreSQL'i ekle ve pytest ile model testlerini yaz.
Başlamadan önce planını göster.
```

## 13. Açık Kararlar

Aşağıdaki noktalar geliştirmeye başlamadan netleşmeli; parantez içindeki değerler bu dokümanda varsayılan olarak kullanıldı.

- [ ] **Uygulama adı:** "Fast Quiz" mi "Rapid Quiz" mi? (Fast Quiz)
- [ ] **Skor tablosu kapsamı:** Sadece kategori bazlı mı, genel tablo da olacak mı? (İkisi de)
- [ ] **Skor tablosu süresi:** Tüm zamanlar mı, haftalık sıfırlanan mı? (Tüm zamanlar; haftalık tablo v2)
- [ ] **Aynı isim:** Aynı isim birden fazla kez listede olabilir mi? (Evet, her oturum ayrı kayıt)
- [ ] **Puanlama:** Karar verildi: hız bonuslu (doğru cevap 100 taban + en fazla 100 hız bonusu, Bölüm 7)
- [ ] **Doğru cevabı gösterme:** Yanlış cevapta doğru şık gösterilsin mi? (Evet, \~0,8 sn)
- [ ] **Mobil teknoloji:** Karar verildi: Vue.js + Capacitor; web ile aynı kod tabanı (Bölüm 8)
- [ ] **Soru kaynağı:** Sorular kim tarafından yazılacak ve kontrol edilecek?
