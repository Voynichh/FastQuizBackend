"""Quiz oturumu, süre doğrulama ve puanlama iş mantığı.

Puan ve süre hesabı SADECE burada yapılır (Bölüm 7). View'lar ve serializer'lar bu
modülü çağırır; istemciden puan/süre alınmaz. Tüm zamanlar sunucu saatidir.
"""

import hashlib
import hmac
import random
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common import exceptions as err
from apps.leaderboard import services as leaderboard
from apps.leaderboard.models import ScoreEntry

from .models import Category, Choice, Question, QuizSession, SessionQuestion

BASE_POINTS = 100
MAX_SPEED_BONUS = 100
CHOICES_PER_QUESTION = 4
_MS = timedelta(milliseconds=1)


# ---- sonuç tipleri ----


@dataclass(frozen=True)
class CurrentQuestion:
    position: int
    total_questions: int
    question_id: int
    text: str
    choices: list[dict]
    time_limit_ms: int
    server_time: datetime
    deadline: datetime
    total_score: int


@dataclass(frozen=True)
class AnswerResult:
    result: str
    correct_choice_id: int
    points: int
    response_ms: int
    total_score: int
    is_last: bool


@dataclass(frozen=True)
class SessionResult:
    category: Category
    total_questions: int
    total_score: int
    correct_count: int
    wrong_count: int
    empty_count: int
    avg_response_ms: int
    estimated_rank: int
    in_top_10: bool
    score_saved: bool


@dataclass(frozen=True)
class SavedScore:
    rank: int
    in_top_10: bool
    score: int


# ---- yardımcılar ----


def _limits() -> tuple[int, int]:
    return settings.QUIZ_TIME_LIMIT_MS, settings.QUIZ_GRACE_MS


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def points_for(response_ms: int, *, correct: bool, time_limit_ms: int) -> int:
    """Doğru cevap: 100 taban + kalan süreye orantılı en fazla 100 bonus (.5 yukarı)."""
    if not correct:
        return 0
    remaining = time_limit_ms - min(max(response_ms, 0), time_limit_ms)
    bonus = (2 * MAX_SPEED_BONUS * remaining + time_limit_ms) // (2 * time_limit_ms)
    return BASE_POINTS + bonus


def _expire_stale(session_id, now: datetime) -> None:
    """Hareketsiz aktif oturumu `abandoned` yapar. Ayrı (atomic dışı) bir yazma olduğu için
    ardından fırlatılacak hata bu değişikliği geri almaz."""
    cutoff = now - timedelta(seconds=settings.QUIZ_SESSION_IDLE_SECONDS)
    QuizSession.objects.filter(
        pk=session_id, status=QuizSession.Status.ACTIVE, last_activity_at__lt=cutoff
    ).update(status=QuizSession.Status.ABANDONED, finished_at=now)


def _lock(session_id) -> QuizSession:
    return QuizSession.objects.select_for_update().get(pk=session_id)


def _ensure_active(session: QuizSession) -> None:
    if session.status == QuizSession.Status.COMPLETED:
        raise err.SessionCompleted
    if session.status == QuizSession.Status.ABANDONED:
        raise err.SessionAbandoned


def _total_questions(session: QuizSession) -> int:
    return session.session_questions.count()


def _complete(session: QuizSession, now: datetime) -> None:
    session.status = QuizSession.Status.COMPLETED
    session.finished_at = now


# ---- oturum ----


def create_session(category: Category, client_type: str) -> tuple[QuizSession, str]:
    """Kategoriden rastgele sorular seçip oturum açar. (oturum, ham token) döner;
    ham token yalnızca burada bilinir, veritabanında özeti tutulur."""
    rng = random.SystemRandom()
    pool = [
        q
        for q in Question.objects.filter(category=category, is_active=True).prefetch_related(
            "choices"
        )
        if _is_playable(q)
    ]
    if len(pool) < settings.QUIZ_QUESTION_COUNT:
        raise err.CategoryUnavailable
    picked = rng.sample(pool, settings.QUIZ_QUESTION_COUNT)

    token = secrets.token_urlsafe(32)
    with transaction.atomic():
        session = QuizSession.objects.create(
            category=category, client_type=client_type, token_hash=_hash_token(token)
        )
        rows = []
        for position, question in enumerate(picked):
            order = [c.id for c in question.choices.all()]
            rng.shuffle(order)
            rows.append(
                SessionQuestion(
                    session=session, question=question, position=position, choice_order=order
                )
            )
        SessionQuestion.objects.bulk_create(rows)
    return session, token


def _is_playable(question: Question) -> bool:
    choices = list(question.choices.all())
    return len(choices) == CHOICES_PER_QUESTION and sum(c.is_correct for c in choices) == 1


def authenticate_session(session_id, token: str | None) -> QuizSession:
    try:
        session = QuizSession.objects.select_related("category").get(pk=session_id)
    except QuizSession.DoesNotExist:
        raise err.NotFound("Oturum bulunamadı.") from None
    if not token or not hmac.compare_digest(_hash_token(token), session.token_hash):
        raise err.InvalidSessionToken
    return session


# ---- sıradaki soru ----


def get_current(session: QuizSession) -> CurrentQuestion:
    """Aktif soruyu verir ve süreyi (ilk çağrıda) başlatır. Tekrar çağrıda aynı `deadline`
    döner. Süresi (ağ toleransı dahil) geçmiş soruyu `timeout` kapatıp sonrakini verir."""
    now = timezone.now()
    _expire_stale(session.pk, now)
    limit, grace = _limits()
    with transaction.atomic():
        locked = _lock(session.pk)
        _ensure_active(locked)
        total = _total_questions(locked)
        row = (
            SessionQuestion.objects.select_related("question")
            .filter(session=locked, position=locked.current_index)
            .first()
        )
        if row is not None and row.served_at is not None:
            if now > row.served_at + (limit + grace) * _MS:
                _close_as_timeout(locked, row, now, limit)
                row = (
                    SessionQuestion.objects.select_related("question")
                    .filter(session=locked, position=locked.current_index)
                    .first()
                )
        if row is None:  # tüm sorular bitti
            _complete(locked, now)
            locked.last_activity_at = now
            locked.save()
            current = None
        else:
            if row.served_at is None:
                row.served_at = now
                row.save(update_fields=["served_at"])
            locked.last_activity_at = now
            locked.save(update_fields=["last_activity_at"])
            choices = Choice.objects.in_bulk(row.choice_order)
            current = CurrentQuestion(
                position=row.position,
                total_questions=total,
                question_id=row.question_id,
                text=row.question.text,
                choices=[{"id": cid, "text": choices[cid].text} for cid in row.choice_order],
                time_limit_ms=limit,
                server_time=now,
                deadline=row.served_at + limit * _MS,
                total_score=locked.total_score,
            )
    if current is None:
        raise err.SessionCompleted
    return current


def _close_as_timeout(session: QuizSession, row: SessionQuestion, now: datetime, limit: int):
    row.answered_at = now
    row.result = SessionQuestion.Result.TIMEOUT
    row.response_ms = limit
    row.points = 0
    row.save(update_fields=["answered_at", "result", "response_ms", "points"])
    session.empty_count += 1
    session.current_index += 1
    session.last_activity_at = now
    session.save()


# ---- cevap ----


def submit_answer(session: QuizSession, question_id: int, choice_id: int | None) -> AnswerResult:
    now = timezone.now()
    _expire_stale(session.pk, now)
    limit, grace = _limits()
    with transaction.atomic():
        locked = _lock(session.pk)
        _ensure_active(locked)
        row = (
            SessionQuestion.objects.select_for_update()
            .select_related("question")
            .filter(session=locked, question_id=question_id)
            .first()
        )
        if row is None:
            raise err.QuestionMismatch
        if row.answered_at is not None:
            raise err.AlreadyAnswered
        if row.position != locked.current_index or row.served_at is None:
            raise err.QuestionMismatch
        if choice_id is not None and choice_id not in row.choice_order:
            raise err.ValidationFailed(
                "Geçersiz şık.", details={"choice_id": ["Şık bu soruya ait değil."]}
            )

        elapsed_ms = (now - row.served_at) // _MS
        correct_id = Choice.objects.values_list("id", flat=True).get(
            question_id=question_id, is_correct=True
        )
        if choice_id is None or elapsed_ms > limit + grace:
            result, selected = SessionQuestion.Result.TIMEOUT, None
            locked.empty_count += 1
        elif choice_id == correct_id:
            result, selected = SessionQuestion.Result.CORRECT, choice_id
            locked.correct_count += 1
        else:
            result, selected = SessionQuestion.Result.WRONG, choice_id
            locked.wrong_count += 1
        points = points_for(
            elapsed_ms, correct=result == SessionQuestion.Result.CORRECT, time_limit_ms=limit
        )

        row.answered_at = now
        row.selected_choice_id = selected
        row.result = result
        row.response_ms = elapsed_ms
        row.points = points
        row.save(
            update_fields=["answered_at", "selected_choice", "result", "response_ms", "points"]
        )

        locked.total_score += points
        locked.current_index += 1
        locked.last_activity_at = now
        is_last = locked.current_index >= _total_questions(locked)
        if is_last:
            _complete(locked, now)
        locked.save()

    return AnswerResult(
        result=result,
        correct_choice_id=correct_id,
        points=points,
        response_ms=elapsed_ms,
        total_score=locked.total_score,
        is_last=is_last,
    )


# ---- sonuç ve skor ----


def _avg_response_ms(session: QuizSession) -> int:
    """Süre aşımı = tam süre; diğerleri en fazla tam süre. Eşitlik bozmada kullanılır."""
    limit, _ = _limits()
    rows = list(session.session_questions.values_list("result", "response_ms"))
    values = [
        limit if result == SessionQuestion.Result.TIMEOUT or ms is None else min(ms, limit)
        for result, ms in rows
    ]
    n = max(len(values), 1)
    return (2 * sum(values) + n) // (2 * n)


def _finished_session(session: QuizSession, now: datetime) -> QuizSession:
    _expire_stale(session.pk, now)
    fresh = QuizSession.objects.select_related("category").get(pk=session.pk)
    if fresh.status == QuizSession.Status.ABANDONED:
        raise err.SessionAbandoned
    if fresh.status != QuizSession.Status.COMPLETED:
        raise err.SessionNotCompleted
    return fresh


def get_result(session: QuizSession) -> SessionResult:
    fresh = _finished_session(session, timezone.now())
    avg = _avg_response_ms(fresh)
    entry = ScoreEntry.objects.filter(session=fresh).first()
    if entry is not None:
        rank = leaderboard.rank_of(entry)
    else:
        rank = leaderboard.estimated_rank(
            fresh.category_id, score=fresh.total_score, avg_response_ms=avg
        )
    return SessionResult(
        category=fresh.category,
        total_questions=_total_questions(fresh),
        total_score=fresh.total_score,
        correct_count=fresh.correct_count,
        wrong_count=fresh.wrong_count,
        empty_count=fresh.empty_count,
        avg_response_ms=avg,
        estimated_rank=rank,
        in_top_10=rank <= settings.LEADERBOARD_SIZE,
        score_saved=entry is not None,
    )


def save_score(session: QuizSession, player_name: str) -> SavedScore:
    """Oturumun puanını skor tablosuna yazar. Puan istemciden alınmaz, oturumdan okunur."""
    now = timezone.now()
    _finished_session(session, now)  # abandoned / tamamlanmamış için erken hata
    with transaction.atomic():
        locked = _lock(session.pk)
        if ScoreEntry.objects.filter(session=locked).exists():
            raise err.ScoreAlreadySaved
        name = leaderboard.validate_player_name(player_name)
        entry = ScoreEntry.objects.create(
            session=locked,
            category_id=locked.category_id,
            player_name=name,
            score=locked.total_score,
            correct_count=locked.correct_count,
            avg_response_ms=_avg_response_ms(locked),
        )
    rank = leaderboard.rank_of(entry)
    return SavedScore(rank=rank, in_top_10=rank <= settings.LEADERBOARD_SIZE, score=entry.score)
