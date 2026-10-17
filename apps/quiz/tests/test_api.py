import datetime as dt
import json
import re
import uuid

import pytest
from django.db import connection
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.quiz.models import Choice
from apps.quiz.tests.factories import CategoryFactory

from .conftest import correct_choice_id, make_question, wrong_choice_id

pytestmark = pytest.mark.django_db

MS = dt.timedelta(milliseconds=1)
ISO_MS_Z = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
BASE = "/api/v1"


@pytest.fixture
def api():
    return APIClient()


def assert_error(response, status, code):
    assert response.status_code == status, response.content
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    return body["error"]


def open_session(api, category, **headers):
    response = api.post(f"{BASE}/sessions/", {"category": category.slug}, format="json", **headers)
    assert response.status_code == 201, response.content
    data = response.json()
    return data["session_id"], data["session_token"], data


def auth(token):
    return {"HTTP_X_SESSION_TOKEN": token}


def current(api, sid, token):
    return api.get(f"{BASE}/sessions/{sid}/current/", **auth(token))


def answer(api, sid, token, question_id, choice_id):
    return api.post(
        f"{BASE}/sessions/{sid}/answers/",
        {"question_id": question_id, "choice_id": choice_id},
        format="json",
        **auth(token),
    )


def play_whole_quiz(api, sid, token, clock, *, ms=1000):
    last = None
    for _ in range(20):
        q = current(api, sid, token).json()["question"]
        clock.shift(ms * MS)
        last = answer(api, sid, token, q["id"], correct_choice_id(q["id"]))
        assert last.status_code == 200
    return last.json()


# ---- kategoriler ----


def test_categories_are_listed_in_order_field_sequence(api):
    for slug, order in (("c", 3), ("a", 1), ("b", 2)):
        CategoryFactory(slug=slug, order=order)
    slugs = [c["slug"] for c in api.get(f"{BASE}/categories/").json()["categories"]]
    assert slugs == ["a", "b", "c"]


def test_categories_list_only_active_with_question_counts(api, category):
    CategoryFactory(slug="gizli", is_active=False)
    make_question(category, is_active=False)  # pasif soru sayılmaz
    response = api.get(f"{BASE}/categories/")
    assert response.status_code == 200
    items = response.json()["categories"]
    assert [c["slug"] for c in items] == ["yapay-zeka"]
    assert items[0]["question_count"] == 25
    assert set(items[0]) == {"slug", "name", "description", "icon", "color", "question_count"}


# ---- oturum açma ----


def test_create_session(api, category, settings):
    response = api.post(f"{BASE}/sessions/", {"category": "yapay-zeka"}, format="json")
    assert response.status_code == 201
    data = response.json()
    uuid.UUID(data["session_id"])
    assert len(data["session_token"]) >= 40
    assert data["category"]["slug"] == "yapay-zeka"
    assert data["total_questions"] == 20
    assert data["time_limit_ms"] == 5000


@pytest.mark.parametrize(
    ("header", "stored"), [(None, "web"), ("ios", "ios"), ("Android", "android")]
)
def test_client_header_is_stored(api, category, header, stored):
    from apps.quiz.models import QuizSession

    headers = {"HTTP_X_CLIENT": header} if header else {}
    sid, _, _ = open_session(api, category, **headers)
    assert QuizSession.objects.get(pk=sid).client_type == stored


def test_unknown_client_is_validation_error(api, category):
    response = api.post(
        f"{BASE}/sessions/", {"category": "yapay-zeka"}, format="json", HTTP_X_CLIENT="toaster"
    )
    assert_error(response, 400, "validation_error")


def test_create_session_unknown_or_inactive_category(api, category):
    CategoryFactory(slug="pasif", is_active=False)
    for slug in ("yok", "pasif"):
        response = api.post(f"{BASE}/sessions/", {"category": slug}, format="json")
        assert_error(response, 404, "not_found")


def test_create_session_validation(api, category):
    assert_error(api.post(f"{BASE}/sessions/", {}, format="json"), 400, "validation_error")
    error = assert_error(
        api.post(f"{BASE}/sessions/", {"category": ""}, format="json"), 400, "validation_error"
    )
    assert "category" in error["details"]


def test_create_session_with_too_few_questions(api):
    category = CategoryFactory(slug="az")
    for _ in range(5):
        make_question(category)
    response = api.post(f"{BASE}/sessions/", {"category": "az"}, format="json")
    assert_error(response, 409, "category_unavailable")


def test_invalid_json_body(api, category):
    response = api.post(f"{BASE}/sessions/", "{kırık", content_type="application/json")
    assert_error(response, 400, "validation_error")


# ---- kimlik doğrulama ----


@pytest.mark.parametrize("path", ["current", "result"])
def test_get_endpoints_need_valid_token(api, category, path):
    sid, token, _ = open_session(api, category)
    url = f"{BASE}/sessions/{sid}/{path}/"
    assert_error(api.get(url), 401, "invalid_session_token")
    assert_error(api.get(url, **auth("yanlis")), 401, "invalid_session_token")


@pytest.mark.parametrize("path", ["answers", "score"])
def test_post_endpoints_need_valid_token(api, category, path):
    sid, token, _ = open_session(api, category)
    url = f"{BASE}/sessions/{sid}/{path}/"
    assert_error(api.post(url, {}, format="json"), 401, "invalid_session_token")


def test_other_sessions_token_is_rejected(api, category):
    sid_a, _, _ = open_session(api, category)
    _, token_b, _ = open_session(api, category)
    assert_error(current(api, sid_a, token_b), 401, "invalid_session_token")


def test_unknown_session_is_404(api, category):
    _, token, _ = open_session(api, category)
    assert_error(current(api, uuid.uuid4(), token), 404, "not_found")


# ---- soru akışı ----


def test_current_response_shape_and_no_answer_leak(api, category, clock):
    sid, token, _ = open_session(api, category)
    response = current(api, sid, token)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "position",
        "total_questions",
        "question",
        "time_limit_ms",
        "server_time",
        "deadline",
        "total_score",
    }
    assert data["position"] == 0
    assert data["total_questions"] == 20
    assert ISO_MS_Z.match(data["server_time"])
    assert ISO_MS_Z.match(data["deadline"])
    assert data["server_time"] == "2026-10-17T08:00:00.000Z"
    assert data["deadline"] == "2026-10-17T08:00:05.000Z"
    question = data["question"]
    assert set(question) == {"id", "text", "choices"}
    assert len(question["choices"]) == 4
    assert all(set(c) == {"id", "text"} for c in question["choices"])
    raw = response.content.decode()
    assert "is_correct" not in raw
    assert "correct" not in raw


def test_refresh_returns_same_deadline(api, category, clock):
    sid, token, _ = open_session(api, category)
    first = current(api, sid, token).json()
    clock.shift(1500 * MS)
    second = current(api, sid, token).json()
    assert second["deadline"] == first["deadline"]
    assert second["question"] == first["question"]
    assert second["server_time"] != first["server_time"]


def test_answer_flow_and_error_codes(api, category, clock):
    sid, token, _ = open_session(api, category)
    q = current(api, sid, token).json()["question"]
    clock.shift(1600 * MS)

    response = answer(api, sid, token, q["id"], correct_choice_id(q["id"]))
    assert response.status_code == 200
    assert response.json() == {
        "result": "correct",
        "correct_choice_id": correct_choice_id(q["id"]),
        "points": 168,
        "response_ms": 1600,
        "total_score": 168,
        "is_last": False,
    }
    assert_error(answer(api, sid, token, q["id"], None), 409, "already_answered")
    assert_error(answer(api, sid, token, 999999, None), 409, "question_mismatch")


def test_answer_validation_errors(api, category):
    sid, token, _ = open_session(api, category)
    url = f"{BASE}/sessions/{sid}/answers/"
    for body in ({}, {"question_id": 1}, {"question_id": "x", "choice_id": None}):
        assert_error(api.post(url, body, format="json", **auth(token)), 400, "validation_error")
    q = current(api, sid, token).json()["question"]
    foreign = Choice.objects.exclude(question_id=q["id"]).first().id
    assert_error(answer(api, sid, token, q["id"], foreign), 400, "validation_error")


def test_wrong_and_timeout_results(api, category, clock):
    sid, token, _ = open_session(api, category)
    q = current(api, sid, token).json()["question"]
    clock.shift(300 * MS)
    wrong = answer(api, sid, token, q["id"], wrong_choice_id(q["id"])).json()
    assert (wrong["result"], wrong["points"]) == ("wrong", 0)
    q2 = current(api, sid, token).json()["question"]
    clock.shift(5000 * MS)
    timeout = answer(api, sid, token, q2["id"], None).json()
    assert (timeout["result"], timeout["points"]) == ("timeout", 0)
    assert timeout["correct_choice_id"] == correct_choice_id(q2["id"])


def test_stale_question_is_closed_on_next_current(api, category, clock):
    sid, token, _ = open_session(api, category)
    first = current(api, sid, token).json()
    clock.shift(6000 * MS)
    second = current(api, sid, token).json()
    assert second["position"] == 1
    assert second["question"]["id"] != first["question"]["id"]


# ---- bitiş, sonuç, skor ----


def test_full_quiz_to_leaderboard(api, category, clock):
    sid, token, _ = open_session(api, category)
    assert_error(
        api.get(f"{BASE}/sessions/{sid}/result/", **auth(token)), 409, "session_not_completed"
    )
    assert_error(
        api.post(
            f"{BASE}/sessions/{sid}/score/", {"player_name": "Ece"}, format="json", **auth(token)
        ),
        409,
        "session_not_completed",
    )

    last = play_whole_quiz(api, sid, token, clock, ms=1000)
    assert last["is_last"] is True
    assert last["total_score"] == 20 * 180

    assert_error(current(api, sid, token), 409, "session_completed")

    result = api.get(f"{BASE}/sessions/{sid}/result/", **auth(token)).json()
    assert result["total_score"] == 3600
    assert (result["correct_count"], result["wrong_count"], result["empty_count"]) == (20, 0, 0)
    assert result["avg_response_ms"] == 1000
    assert result["estimated_rank"] == 1
    assert result["in_top_10"] is True
    assert result["score_saved"] is False
    assert result["category"]["slug"] == "yapay-zeka"

    saved = api.post(
        f"{BASE}/sessions/{sid}/score/",
        {"player_name": "  Ece  ", "score": 999999},  # istemci puanı yok sayılır
        format="json",
        **auth(token),
    )
    assert saved.status_code == 201
    assert saved.json() == {"rank": 1, "in_top_10": True, "score": 3600}
    assert_error(
        api.post(
            f"{BASE}/sessions/{sid}/score/", {"player_name": "Ece"}, format="json", **auth(token)
        ),
        409,
        "score_already_saved",
    )

    board = api.get(f"{BASE}/leaderboard/?category=yapay-zeka").json()
    assert board["category"] == "yapay-zeka"
    assert len(board["entries"]) == 1
    entry = board["entries"][0]
    assert set(entry) == {
        "rank",
        "player_name",
        "score",
        "correct_count",
        "avg_response_ms",
        "created_at",
    }
    assert (entry["rank"], entry["player_name"], entry["score"]) == (1, "Ece", 3600)
    assert ISO_MS_Z.match(entry["created_at"])
    assert api.get(f"{BASE}/leaderboard/").json()["category"] is None
    assert len(api.get(f"{BASE}/leaderboard/").json()["entries"]) == 1
    assert api.get(f"{BASE}/sessions/{sid}/result/", **auth(token)).json()["score_saved"] is True


@pytest.mark.parametrize("name", ["", "x", "a" * 21, "Ece!", "<script>", "orospu", "s i k t i r"])
def test_score_rejects_invalid_names(api, category, clock, name):
    sid, token, _ = open_session(api, category)
    play_whole_quiz(api, sid, token, clock)
    response = api.post(
        f"{BASE}/sessions/{sid}/score/", {"player_name": name}, format="json", **auth(token)
    )
    error = assert_error(response, 400, "validation_error")
    assert "player_name" in error["details"]
    # kayıt oluşmadı; geçerli isimle yeniden denenebilir
    ok = api.post(
        f"{BASE}/sessions/{sid}/score/", {"player_name": "Ece"}, format="json", **auth(token)
    )
    assert ok.status_code == 201


def test_score_requires_player_name_field(api, category, clock):
    sid, token, _ = open_session(api, category)
    play_whole_quiz(api, sid, token, clock)
    response = api.post(f"{BASE}/sessions/{sid}/score/", {}, format="json", **auth(token))
    assert_error(response, 400, "validation_error")


def test_leaderboard_unknown_category(api, category):
    assert_error(api.get(f"{BASE}/leaderboard/?category=yok"), 404, "not_found")


def test_leaderboard_empty(api, category):
    assert api.get(f"{BASE}/leaderboard/?category=yapay-zeka").json()["entries"] == []


def test_abandoned_session_responses(api, category, clock):
    sid, token, _ = open_session(api, category)
    clock.shift(dt.timedelta(minutes=11))
    assert_error(current(api, sid, token), 409, "session_abandoned")
    assert_error(
        api.post(
            f"{BASE}/sessions/{sid}/score/", {"player_name": "Ece"}, format="json", **auth(token)
        ),
        409,
        "session_abandoned",
    )


# ---- genel davranış ----


def test_unknown_api_path_returns_json_404(api):
    assert_error(api.get(f"{BASE}/yok/"), 404, "not_found")


def test_there_is_no_admin_panel(client):
    for path in ("/yonetim/", "/admin/", "/yonetim/login/"):
        assert client.get(path).status_code == 404


def test_method_not_allowed_uses_error_format(api, category):
    assert_error(api.delete(f"{BASE}/categories/"), 405, "method_not_allowed")


def test_wrong_content_type_uses_error_format(api, category):
    response = api.post(f"{BASE}/sessions/", "category=yapay-zeka", content_type="text/plain")
    assert_error(response, 415, "unsupported_media_type")


def test_health_ok_even_with_unlisted_host(client, settings):
    response = client.get("/api/v1/health/", HTTP_HOST="10.1.2.3")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_database_failure(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(connection, "cursor", boom)
    response = client.get("/api/v1/health/")
    assert response.status_code == 503


def test_schema_and_docs_are_served(client):
    schema = client.get(f"{BASE}/schema/", HTTP_ACCEPT="application/json")
    assert schema.status_code == 200
    paths = json.loads(schema.content)["paths"]
    assert {
        "/api/v1/categories/",
        "/api/v1/sessions/",
        "/api/v1/sessions/{session_id}/current/",
        "/api/v1/sessions/{session_id}/answers/",
        "/api/v1/sessions/{session_id}/result/",
        "/api/v1/sessions/{session_id}/score/",
        "/api/v1/leaderboard/",
    } <= set(paths)
    assert client.get(f"{BASE}/docs/").status_code == 200


def test_cors_allows_session_headers(client):
    response = client.options(
        f"{BASE}/sessions/",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-session-token,x-client,content-type",
    )
    assert response["Access-Control-Allow-Origin"] == "http://localhost:5173"
    allowed = response["Access-Control-Allow-Headers"].lower()
    assert "x-session-token" in allowed
    assert "x-client" in allowed


def test_dev_cors_accepts_any_local_port_but_not_other_hosts(client):
    """Vite portu değişse (5174, 5175...) de yerel arayüz API'ye ulaşabilmeli."""
    for origin in ("http://localhost:5174", "http://127.0.0.1:5199", "http://[::1]:5180"):
        response = client.get(f"{BASE}/categories/", HTTP_ORIGIN=origin)
        assert response["Access-Control-Allow-Origin"] == origin
    for origin in (
        "http://evil.example",
        "http://localhost.evil.example:5173",
        "https://localhost:5173",
    ):
        response = client.get(f"{BASE}/categories/", HTTP_ORIGIN=origin)
        assert "Access-Control-Allow-Origin" not in response


# ---- rate limit ----


def test_session_create_is_rate_limited(api, category):
    for _ in range(10):
        assert (
            api.post(f"{BASE}/sessions/", {"category": "yapay-zeka"}, format="json").status_code
            == 201
        )
    response = api.post(f"{BASE}/sessions/", {"category": "yapay-zeka"}, format="json")
    error = assert_error(response, 429, "rate_limited")
    assert error["details"]["retry_after_seconds"] >= 1
    assert "Retry-After" in response


def test_answers_and_score_limits(api, category, clock, monkeypatch):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "answers", "3/min")
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "score", "1/min")
    sid, token, _ = open_session(api, category)
    for _ in range(3):
        q = current(api, sid, token).json()["question"]
        assert answer(api, sid, token, q["id"], None).status_code == 200
    q = current(api, sid, token).json()["question"]
    assert_error(answer(api, sid, token, q["id"], None), 429, "rate_limited")

    url = f"{BASE}/sessions/{sid}/score/"
    assert api.post(url, {"player_name": "x"}, format="json", **auth(token)).status_code != 429
    assert_error(
        api.post(url, {"player_name": "x"}, format="json", **auth(token)), 429, "rate_limited"
    )
