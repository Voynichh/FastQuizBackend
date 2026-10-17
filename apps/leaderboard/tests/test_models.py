from datetime import timedelta

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.leaderboard.models import ScoreEntry
from apps.quiz.tests.factories import CategoryFactory, QuizSessionFactory

pytestmark = pytest.mark.django_db


def make_entry(category, score, avg_ms=2000, name="Ece", created_at=None):
    entry = ScoreEntry.objects.create(
        session=QuizSessionFactory(category=category),
        category=category,
        player_name=name,
        score=score,
        correct_count=10,
        avg_response_ms=avg_ms,
    )
    if created_at:
        ScoreEntry.objects.filter(pk=entry.pk).update(created_at=created_at)
    return entry


def test_one_score_entry_per_session():
    category = CategoryFactory()
    session = QuizSessionFactory(category=category)
    kwargs = dict(
        session=session, category=category, player_name="Ece", score=100,
        correct_count=1, avg_response_ms=1000,
    )  # fmt: skip
    ScoreEntry.objects.create(**kwargs)
    with pytest.raises(IntegrityError), transaction.atomic():
        ScoreEntry.objects.create(**kwargs)


def test_ranking_order_score_then_speed_then_time():
    category = CategoryFactory()
    now = timezone.now()
    low = make_entry(category, 1000)
    slow = make_entry(category, 2000, avg_ms=3000)
    fast = make_entry(category, 2000, avg_ms=1500)
    tie_late = make_entry(category, 2000, avg_ms=1500, created_at=now + timedelta(minutes=1))
    tie_early = make_entry(category, 2000, avg_ms=1500, created_at=now - timedelta(minutes=1))
    assert list(ScoreEntry.objects.all()) == [tie_early, fast, tie_late, slow, low]


def test_same_player_name_can_appear_multiple_times():
    category = CategoryFactory()
    make_entry(category, 100, name="Ece")
    make_entry(category, 200, name="Ece")
    assert ScoreEntry.objects.filter(player_name="Ece").count() == 2


def test_rank_indexes_exist_with_expected_columns():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'leaderboard_scoreentry'"
        )
        defs = dict(cursor.fetchall())
    assert (
        "(category_id, score DESC, avg_response_ms, created_at)" in defs["score_category_rank_idx"]
    )
    assert "(score DESC, avg_response_ms, created_at)" in defs["score_global_rank_idx"]
