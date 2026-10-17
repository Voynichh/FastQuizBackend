import pytest

from apps.common.exceptions import ApiError
from apps.leaderboard import services
from apps.leaderboard.models import ScoreEntry
from apps.quiz.tests.factories import CategoryFactory, QuizSessionFactory

# ---- isim filtresi (saf fonksiyon, veritabanı gerekmez) ----


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ece", "Ece"),
        ("  Ece  ", "Ece"),
        ("Çağrı Şen", "Çağrı Şen"),
        ("ali_veli-99.x", "ali_veli-99.x"),
        ("Ab", "Ab"),
        ("a" * 20, "a" * 20),
    ],
)
def test_valid_names(raw, expected):
    assert services.validate_player_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", " ", "a", "a" * 21, "  a  ", "Ece!", "<b>Ece</b>", "ece@x", "ece😀", "a\nb", "Ece\tx"],
)
def test_invalid_names(raw):
    with pytest.raises(ApiError) as exc:
        services.validate_player_name(raw)
    assert exc.value.code == "validation_error"
    assert "player_name" in exc.value.details


@pytest.mark.parametrize(
    "raw",
    [
        "amk",
        "AMK",
        "Siktir",
        "s i k t i r",
        "sıktır",
        "orospu",
        "0rospu",
        "fuck",
        "FuCk_you",
        "f.u.c.k",
        "shiit",
        "b1tch",
        "ibne",
        "Pezevenk",
    ],
)
def test_profanity_is_rejected(raw):
    with pytest.raises(ApiError) as exc:
        services.validate_player_name(raw)
    assert exc.value.code == "validation_error"


@pytest.mark.parametrize(
    "raw",
    ["Kamil", "Sikke", "Basit", "Assassin", "Scunthorpe", "Dickens", "Pickle", "Gotham", "Aqua"],
)
def test_innocent_names_with_profane_substrings_pass(raw):
    assert services.validate_player_name(raw) == raw


# ---- sıralama ----

pytestmark_db = pytest.mark.django_db


def entry(category, score, avg_ms=2000, name="X"):
    return ScoreEntry.objects.create(
        session=QuizSessionFactory(category=category),
        category=category,
        player_name=name,
        score=score,
        correct_count=10,
        avg_response_ms=avg_ms,
    )


@pytest.mark.django_db
def test_top_entries_limited_and_ordered_per_category(settings):
    settings.LEADERBOARD_SIZE = 3
    a, b = CategoryFactory(), CategoryFactory()
    for s in (100, 500, 300, 400, 200):
        entry(a, s)
    entry(b, 9999)
    rows = services.top_entries(a)
    assert [r["score"] for r in rows] == [500, 400, 300]
    assert [r["rank"] for r in rows] == [1, 2, 3]


@pytest.mark.django_db
def test_top_entries_global_mixes_categories():
    a, b = CategoryFactory(), CategoryFactory()
    entry(a, 100)
    entry(b, 300)
    assert [r["score"] for r in services.top_entries(None)] == [300, 100]


@pytest.mark.django_db
def test_rank_of_uses_full_tiebreak_chain():
    c = CategoryFactory()
    first = entry(c, 1000, avg_ms=1000)
    second = entry(c, 1000, avg_ms=1000)  # aynı puan ve süre: önce kaydeden üstte
    third = entry(c, 1000, avg_ms=1500)
    fourth = entry(c, 900, avg_ms=100)
    assert [services.rank_of(e) for e in (first, second, third, fourth)] == [1, 2, 3, 4]


@pytest.mark.django_db
def test_estimated_rank_for_hypothetical_score():
    c = CategoryFactory()
    entry(c, 1000, avg_ms=1000)
    entry(c, 800)
    assert services.estimated_rank(c, score=1000, avg_response_ms=1000) == 2  # eşitlikte sona
    assert services.estimated_rank(c, score=1000, avg_response_ms=900) == 1
    assert services.estimated_rank(c, score=900, avg_response_ms=1) == 2
    assert services.estimated_rank(c, score=100, avg_response_ms=1) == 3
