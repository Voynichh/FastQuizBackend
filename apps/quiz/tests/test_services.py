import datetime as dt
import hashlib
import threading

import pytest
from django.db import connection

from apps.common import exceptions as err
from apps.leaderboard.models import ScoreEntry
from apps.quiz import services
from apps.quiz.models import QuizSession, SessionQuestion

from .conftest import correct_choice_id, wrong_choice_id

pytestmark = pytest.mark.django_db

MS = dt.timedelta(milliseconds=1)


def start(category):
    session, token = services.create_session(category, "web")
    return session, token


def play_correct(session, clock, ms=1000):
    """Aktif soruyu `ms` sonra doğru cevaplar."""
    current = services.get_current(session)
    clock.shift(ms * MS)
    return services.submit_answer(
        session, current.question_id, correct_choice_id(current.question_id)
    )


# ---- puan formülü ----


@pytest.mark.parametrize(
    ("response_ms", "expected"),
    [(0, 200), (1600, 168), (2500, 150), (4900, 102), (5000, 100), (5500, 100)],
)
def test_points_for_correct_answers(response_ms, expected):
    assert services.points_for(response_ms, correct=True, time_limit_ms=5000) == expected


def test_points_zero_for_wrong_and_late():
    assert services.points_for(1000, correct=False, time_limit_ms=5000) == 0


def test_points_rounding_is_half_up():
    # bonus = 100 * (5000 - t) / 5000; .5 her zaman yukarı yuvarlanır
    assert services.points_for(4999, correct=True, time_limit_ms=5000) == 100  # 0,02
    assert services.points_for(2475, correct=True, time_limit_ms=5000) == 151  # 50,5
    assert services.points_for(2525, correct=True, time_limit_ms=5000) == 150  # 49,5


# ---- oturum oluşturma ----


def test_create_session_picks_20_distinct_questions_with_shuffled_choices(category):
    session, token = start(category)
    rows = list(session.session_questions.order_by("position"))
    assert [r.position for r in rows] == list(range(20))
    assert len({r.question_id for r in rows}) == 20
    for row in rows:
        ids = set(row.question.choices.values_list("id", flat=True))
        assert set(row.choice_order) == ids
        assert len(row.choice_order) == 4
        assert row.served_at is None


def test_token_is_stored_hashed(category):
    session, token = start(category)
    assert session.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in session.token_hash
    assert len(token) >= 40


def test_create_session_needs_enough_questions(category):
    ids = list(category.questions.values_list("id", flat=True)[:10])
    category.questions.filter(id__in=ids).update(is_active=False)
    with pytest.raises(err.CategoryUnavailable):
        start(category)


def test_inactive_questions_are_not_picked(category, settings):
    settings.QUIZ_QUESTION_COUNT = 20
    inactive = list(category.questions.values_list("id", flat=True)[:5])
    category.questions.filter(id__in=inactive).update(is_active=False)
    session, _ = start(category)
    picked = set(session.session_questions.values_list("question_id", flat=True))
    assert not picked & set(inactive)


# ---- kimlik doğrulama ----


def test_authenticate_session(category):
    session, token = start(category)
    assert services.authenticate_session(session.id, token).id == session.id


@pytest.mark.parametrize("bad", [None, "", "yanlis"])
def test_authenticate_rejects_bad_token(category, bad):
    session, _ = start(category)
    with pytest.raises(err.InvalidSessionToken):
        services.authenticate_session(session.id, bad)


def test_authenticate_unknown_session(category):
    import uuid

    with pytest.raises(err.NotFound):
        services.authenticate_session(uuid.uuid4(), "x")


# ---- sıradaki soru ----


def test_current_starts_timer_and_is_idempotent(category, clock):
    session, _ = start(category)
    first = services.get_current(session)
    assert first.position == 0
    assert first.total_questions == 20
    assert first.time_limit_ms == 5000
    assert first.deadline == first.server_time + 5000 * MS
    clock.shift(2000 * MS)
    again = services.get_current(session)
    assert again.question_id == first.question_id
    assert again.deadline == first.deadline  # yeni süre başlamaz
    assert again.server_time == first.server_time + 2000 * MS


def test_current_choices_follow_stored_order_and_hide_correct_flag(category):
    session, _ = start(category)
    current = services.get_current(session)
    row = session.session_questions.get(position=0)
    assert [c["id"] for c in current.choices] == row.choice_order
    assert all(set(c) == {"id", "text"} for c in current.choices)


def test_current_closes_expired_question_as_timeout_and_serves_next(category, clock):
    session, _ = start(category)
    first = services.get_current(session)
    clock.shift(5501 * MS)  # süre + ağ toleransı geçti
    second = services.get_current(session)
    assert second.position == 1
    assert second.question_id != first.question_id
    closed = session.session_questions.get(position=0)
    assert closed.result == SessionQuestion.Result.TIMEOUT
    assert closed.points == 0
    session.refresh_from_db()
    assert session.empty_count == 1
    assert session.current_index == 1


def test_current_within_grace_still_returns_same_question(category, clock):
    session, _ = start(category)
    first = services.get_current(session)
    clock.shift(5300 * MS)
    assert services.get_current(session).question_id == first.question_id


# ---- cevap gönderme ----


def test_correct_answer_scores_with_speed_bonus(category, clock):
    session, _ = start(category)
    result = play_correct(session, clock, ms=1600)
    assert result.result == "correct"
    assert result.points == 168
    assert result.response_ms == 1600
    assert result.total_score == 168
    assert result.is_last is False
    assert result.correct_choice_id == correct_choice_id(
        session.session_questions.get(position=0).question_id
    )


def test_wrong_answer_gets_zero_and_reveals_correct_choice(category, clock):
    session, _ = start(category)
    current = services.get_current(session)
    clock.shift(500 * MS)
    result = services.submit_answer(
        session, current.question_id, wrong_choice_id(current.question_id)
    )
    assert result.result == "wrong"
    assert result.points == 0
    assert result.correct_choice_id == correct_choice_id(current.question_id)
    session.refresh_from_db()
    assert session.wrong_count == 1


def test_null_choice_is_timeout(category, clock):
    session, _ = start(category)
    current = services.get_current(session)
    clock.shift(5000 * MS)
    result = services.submit_answer(session, current.question_id, None)
    assert result.result == "timeout"
    assert result.points == 0
    session.refresh_from_db()
    assert session.empty_count == 1


def test_answer_within_grace_is_accepted_with_capped_bonus(category, clock):
    session, _ = start(category)
    result = play_correct(session, clock, ms=5400)
    assert result.result == "correct"
    assert result.points == 100


def test_answer_after_grace_is_timeout(category, clock):
    session, _ = start(category)
    result = play_correct(session, clock, ms=5501)
    assert result.result == "timeout"
    assert result.points == 0


def test_second_answer_to_same_question_is_rejected(category, clock):
    session, _ = start(category)
    current = services.get_current(session)
    choice = correct_choice_id(current.question_id)
    services.submit_answer(session, current.question_id, choice)
    with pytest.raises(err.AlreadyAnswered):
        services.submit_answer(session, current.question_id, choice)


def test_answer_for_other_question_is_mismatch(category, clock):
    session, _ = start(category)
    services.get_current(session)
    future = session.session_questions.get(position=3)
    with pytest.raises(err.QuestionMismatch):
        services.submit_answer(session, future.question_id, correct_choice_id(future.question_id))
    with pytest.raises(err.QuestionMismatch):
        services.submit_answer(session, 999999, None)


def test_answer_before_question_was_served_is_mismatch(category):
    session, _ = start(category)
    first = session.session_questions.get(position=0)
    with pytest.raises(err.QuestionMismatch):
        services.submit_answer(session, first.question_id, correct_choice_id(first.question_id))


def test_choice_from_another_question_is_validation_error(category, clock):
    session, _ = start(category)
    current = services.get_current(session)
    other = session.session_questions.get(position=1).question_id
    with pytest.raises(err.ApiError) as exc:
        services.submit_answer(session, current.question_id, correct_choice_id(other))
    assert exc.value.code == "validation_error"


def test_next_question_is_not_served_until_requested(category, clock):
    session, _ = start(category)
    play_correct(session, clock)
    assert session.session_questions.get(position=1).served_at is None


# ---- oturum sonu, sonuç ve skor ----


def finish_quiz(session, clock, *, correct=20, ms=1000):
    for i in range(20):
        current = services.get_current(session)
        clock.shift(ms * MS)
        choice = (
            correct_choice_id(current.question_id)
            if i < correct
            else wrong_choice_id(current.question_id)
        )
        last = services.submit_answer(session, current.question_id, choice)
    return last


def test_last_answer_completes_session(category, clock):
    session, _ = start(category)
    last = finish_quiz(session, clock)
    assert last.is_last is True
    session.refresh_from_db()
    assert session.status == QuizSession.Status.COMPLETED
    assert session.finished_at is not None
    assert session.correct_count == 20
    assert session.total_score == 20 * (100 + 80)
    with pytest.raises(err.SessionCompleted):
        services.get_current(session)


def test_answer_after_completion_is_rejected(category, clock):
    session, _ = start(category)
    finish_quiz(session, clock)
    row = session.session_questions.get(position=19)
    with pytest.raises(err.SessionCompleted):
        services.submit_answer(session, row.question_id, None)


def test_result_requires_completion(category):
    session, _ = start(category)
    with pytest.raises(err.SessionNotCompleted):
        services.get_result(session)


def test_result_summary(category, clock):
    session, _ = start(category)
    finish_quiz(session, clock, correct=15, ms=2000)
    result = services.get_result(session)
    assert (result.correct_count, result.wrong_count, result.empty_count) == (15, 5, 0)
    assert result.total_score == 15 * 160
    assert result.avg_response_ms == 2000
    assert result.estimated_rank == 1
    assert result.score_saved is False


def test_timeouts_count_as_full_time_in_average(category, clock):
    session, _ = start(category)
    for i in range(20):
        current = services.get_current(session)
        if i < 10:
            clock.shift(1000 * MS)
            services.submit_answer(
                session, current.question_id, correct_choice_id(current.question_id)
            )
        else:
            clock.shift(5000 * MS)
            services.submit_answer(session, current.question_id, None)
    assert services.get_result(session).avg_response_ms == 3000


def test_save_score_creates_entry_from_session_not_client(category, clock):
    session, _ = start(category)
    finish_quiz(session, clock, correct=20, ms=1000)
    saved = services.save_score(session, "  Ece  ")
    session.refresh_from_db()
    assert (saved.rank, saved.in_top_10, saved.score) == (1, True, session.total_score)
    entry = ScoreEntry.objects.get(session=session)
    assert entry.player_name == "Ece"
    assert entry.score == session.total_score
    assert entry.correct_count == 20
    assert entry.avg_response_ms == 1000
    assert entry.category_id == category.id


def test_score_can_be_saved_only_once(category, clock):
    session, _ = start(category)
    finish_quiz(session, clock)
    services.save_score(session, "Ece")
    with pytest.raises(err.ScoreAlreadySaved):
        services.save_score(session, "Ece")
    assert ScoreEntry.objects.count() == 1
    assert services.get_result(session).score_saved is True


def test_score_requires_completed_session(category):
    session, _ = start(category)
    with pytest.raises(err.SessionNotCompleted):
        services.save_score(session, "Ece")


def test_invalid_name_is_rejected_and_nothing_saved(category, clock):
    session, _ = start(category)
    finish_quiz(session, clock)
    with pytest.raises(err.ApiError) as exc:
        services.save_score(session, "x")
    assert exc.value.code == "validation_error"
    assert "player_name" in exc.value.details
    assert ScoreEntry.objects.count() == 0


def test_rank_reflects_existing_entries(category, clock):
    ranks = []
    for ms in (3000, 1000, 2000):  # daha hızlı olan üste çıkar
        session, _ = start(category)
        finish_quiz(session, clock, ms=ms)
        ranks.append(services.save_score(session, f"P{ms}").rank)
    assert ranks == [1, 1, 2]


# ---- terk edilen oturum ----


def test_idle_session_becomes_abandoned(category, clock):
    session, _ = start(category)
    services.get_current(session)
    clock.shift(dt.timedelta(minutes=10, seconds=1))
    with pytest.raises(err.SessionAbandoned):
        services.get_current(session)
    session.refresh_from_db()
    assert session.status == QuizSession.Status.ABANDONED


def test_activity_keeps_session_alive(category, clock):
    session, _ = start(category)
    for _ in range(3):
        clock.shift(dt.timedelta(minutes=6))
        current = services.get_current(session)
        services.submit_answer(session, current.question_id, None)
    session.refresh_from_db()
    assert session.status == QuizSession.Status.ACTIVE


def test_abandoned_session_cannot_save_score(category, clock):
    session, _ = start(category)
    clock.shift(dt.timedelta(minutes=11))
    with pytest.raises(err.SessionAbandoned):
        services.save_score(session, "Ece")
    assert ScoreEntry.objects.count() == 0


def test_completed_session_never_expires(category, clock):
    session, _ = start(category)
    finish_quiz(session, clock)
    clock.shift(dt.timedelta(hours=2))
    assert services.save_score(session, "Ece").rank == 1


# ---- eşzamanlılık ----


@pytest.mark.django_db(transaction=True)
def test_concurrent_answers_to_same_question_record_exactly_one(category):
    session, _ = start(category)
    current = services.get_current(session)
    choice = correct_choice_id(current.question_id)
    barrier = threading.Barrier(2)
    outcomes = []

    def worker():
        try:
            barrier.wait()
            services.submit_answer(session, current.question_id, choice)
            outcomes.append("ok")
        except err.ApiError as exc:
            outcomes.append(exc.code)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(outcomes) == ["already_answered", "ok"]
    session.refresh_from_db()
    assert session.correct_count == 1
    assert session.current_index == 1
    assert session.session_questions.filter(answered_at__isnull=False).count() == 1
