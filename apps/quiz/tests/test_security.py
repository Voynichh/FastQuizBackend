"""Güvenlik incelemesi bulgularının regresyon testleri (rate limit, bot skoru, temizlik, sağlık)."""

import datetime as dt

import pytest
from django.core.management import call_command
from django.db import connection
from rest_framework.test import APIClient

from apps.common import exceptions as err
from apps.common import middleware
from apps.leaderboard.models import ScoreEntry
from apps.quiz import services
from apps.quiz.models import QuizSession, SessionQuestion

from .conftest import correct_choice_id

pytestmark = pytest.mark.django_db

MS = dt.timedelta(milliseconds=1)
BASE = "/api/v1"


def play(category, clock, ms):
    session, token = services.create_session(category, "web")
    for _ in range(20):
        current = services.get_current(session)
        clock.shift(ms * MS)
        services.submit_answer(session, current.question_id, correct_choice_id(current.question_id))
    return session, token


# ---- Y1: X-Forwarded-For ile rate limit atlatma ----


def post_session(api, xff=None):
    headers = {"HTTP_X_FORWARDED_FOR": xff} if xff else {}
    return api.post(f"{BASE}/sessions/", {"category": "yapay-zeka"}, format="json", **headers)


def test_spoofed_x_forwarded_for_cannot_bypass_rate_limit(category):
    api = APIClient()
    statuses = [post_session(api, xff=f"10.0.0.{i}").status_code for i in range(1, 13)]
    assert statuses[:10] == [201] * 10
    assert statuses[10:] == [429, 429]  # her istekte farklı XFF gönderilse de aynı kova


def test_real_client_address_is_the_identity_by_default(category):
    a, b = APIClient(REMOTE_ADDR="198.51.100.1"), APIClient(REMOTE_ADDR="198.51.100.2")
    for _ in range(10):
        assert post_session(a).status_code == 201
    assert post_session(a).status_code == 429
    assert post_session(b).status_code == 201  # başka gerçek IP başka kova


def test_trusted_proxy_count_makes_forwarded_header_count(category, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    api = APIClient()
    # Tek güvenilir proxy: zincirin son halkası (proxy'nin eklediği gerçek istemci) kullanılır
    for _ in range(10):
        assert post_session(api, xff="203.0.113.9").status_code == 201
    assert post_session(api, xff="203.0.113.9").status_code == 429
    assert post_session(api, xff="203.0.113.10").status_code == 201


# ---- Y2: aşırı hızlı (bot benzeri) oturumlar skor tabloya yazılamaz ----


def test_bot_speed_session_cannot_be_saved(category, clock):
    session, _ = play(category, clock, ms=150)  # 20/20 doğru, ortalama 150 ms
    result = services.get_result(session)
    assert result.avg_response_ms == 150
    with pytest.raises(err.ScoreRejected):
        services.save_score(session, "Robot")
    assert ScoreEntry.objects.count() == 0


def test_plausibility_threshold_is_inclusive_and_configurable(category, clock, settings):
    settings.QUIZ_MIN_PLAUSIBLE_AVG_MS = 700
    session, _ = play(category, clock, ms=700)
    assert services.save_score(session, "Ece").rank == 1

    settings.QUIZ_MIN_PLAUSIBLE_AVG_MS = 1500
    session, _ = play(category, clock, ms=1000)
    with pytest.raises(err.ScoreRejected):
        services.save_score(session, "Can")
    settings.QUIZ_MIN_PLAUSIBLE_AVG_MS = 900
    assert services.save_score(session, "Can").rank >= 1


def test_score_rejected_over_http(category, clock):
    api = APIClient()
    session, token = play(category, clock, ms=100)
    response = api.post(
        f"{BASE}/sessions/{session.id}/score/",
        {"player_name": "Robot"},
        format="json",
        HTTP_X_SESSION_TOKEN=token,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "score_rejected"
    # sonuç ekranı yine de açılabilir (oyuncu cezalandırılmaz, yalnızca tabloya yazılmaz)
    assert services.get_result(session).total_score > 0


def test_timeouts_count_as_slow_so_they_do_not_make_a_session_look_botlike(category, clock):
    session, _ = services.create_session(category, "web")
    for _ in range(20):
        current = services.get_current(session)
        clock.shift(5000 * MS)
        services.submit_answer(session, current.question_id, None)
    assert services.get_result(session).avg_response_ms == 5000


# ---- D3: eski oturum temizliği ----


def run_purge(*args):
    call_command("purge_stale_sessions", *args, verbosity=0)


def test_purge_removes_old_unfinished_sessions_but_keeps_recent_ones(category, clock):
    old, _ = services.create_session(category, "web")
    services.get_current(old)
    clock.shift(dt.timedelta(hours=25))
    recent, _ = services.create_session(category, "web")

    run_purge()

    assert not QuizSession.objects.filter(pk=old.pk).exists()
    assert not SessionQuestion.objects.filter(session_id=old.pk).exists()  # cascade
    assert QuizSession.objects.filter(pk=recent.pk).exists()


def test_purge_never_touches_sessions_with_a_saved_score(category, clock):
    saved, _ = play(category, clock, ms=1000)
    services.save_score(saved, "Ece")
    unsaved, _ = play(category, clock, ms=1000)
    clock.shift(dt.timedelta(days=30))

    run_purge()

    assert QuizSession.objects.filter(pk=saved.pk).exists()
    assert ScoreEntry.objects.filter(session=saved).exists()
    assert not QuizSession.objects.filter(pk=unsaved.pk).exists()


def test_purge_dry_run_deletes_nothing(category, clock):
    session, _ = services.create_session(category, "web")
    clock.shift(dt.timedelta(days=3))
    run_purge("--dry-run")
    assert QuizSession.objects.filter(pk=session.pk).exists()


def test_purge_keeps_recently_completed_unsaved_sessions(category, clock):
    session, _ = play(category, clock, ms=1000)
    clock.shift(dt.timedelta(days=2))  # 7 günden az: oyuncu hâlâ kaydedebilir
    run_purge()
    assert QuizSession.objects.filter(pk=session.pk).exists()


# ---- D4: sağlık ucu veritabanını sık sorgulamaz ----


def test_health_queries_database_at_most_once_per_window(client, monkeypatch):
    calls = []
    real_cursor = connection.cursor

    def counting_cursor(*args, **kwargs):
        calls.append(1)
        return real_cursor(*args, **kwargs)

    clock = {"now": 1000.0}
    monkeypatch.setattr(middleware.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(connection, "cursor", counting_cursor)

    for _ in range(25):
        assert client.get(f"{BASE}/health/").status_code == 200
    assert len(calls) == 1

    clock["now"] += middleware.HEALTH_CACHE_SECONDS + 0.1
    assert client.get(f"{BASE}/health/").status_code == 200
    assert len(calls) == 2


def test_health_failure_is_cached_too_and_recovers(client, monkeypatch):
    clock = {"now": 50.0}
    monkeypatch.setattr(middleware.time, "monotonic", lambda: clock["now"])

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    with monkeypatch.context() as m:
        m.setattr(connection, "cursor", boom)
        assert client.get(f"{BASE}/health/").status_code == 503
    # veritabanı döndü ama sonuç henüz önbellekte: aynı pencerede 503 devam eder
    assert client.get(f"{BASE}/health/").status_code == 503
    clock["now"] += middleware.HEALTH_CACHE_SECONDS + 0.1
    assert client.get(f"{BASE}/health/").status_code == 200
