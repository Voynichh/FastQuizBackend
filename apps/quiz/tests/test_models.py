import pytest
from django.db import IntegrityError, transaction

from apps.quiz.models import Question, QuizSession

from .factories import (
    CategoryFactory,
    ChoiceFactory,
    QuestionFactory,
    QuizSessionFactory,
    SessionQuestionFactory,
)

pytestmark = pytest.mark.django_db


def test_one_correct_choice_per_question():
    question = QuestionFactory()
    ChoiceFactory(question=question, is_correct=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        ChoiceFactory(question=question, is_correct=True)


def test_many_wrong_choices_allowed_and_other_question_can_have_correct():
    question = QuestionFactory()
    ChoiceFactory.create_batch(3, question=question, is_correct=False)
    ChoiceFactory(question=question, is_correct=True)
    ChoiceFactory(question=QuestionFactory(), is_correct=True)
    assert question.choices.count() == 4


@pytest.mark.parametrize("difficulty", [0, 4])
def test_difficulty_must_be_between_1_and_3(difficulty):
    with pytest.raises(IntegrityError), transaction.atomic():
        QuestionFactory(difficulty=difficulty)


def test_category_slug_unique():
    CategoryFactory(slug="fizik")
    with pytest.raises(IntegrityError), transaction.atomic():
        CategoryFactory(slug="fizik")


def test_session_defaults():
    session = QuizSessionFactory()
    assert session.status == QuizSession.Status.ACTIVE
    assert session.client_type == QuizSession.ClientType.WEB
    assert session.current_index == 0
    assert len(session.token_hash) == 64
    assert session.finished_at is None


def test_session_question_position_unique_per_session():
    session = QuizSessionFactory()
    SessionQuestionFactory(session=session, position=0)
    with pytest.raises(IntegrityError), transaction.atomic():
        SessionQuestionFactory(session=session, position=0)


def test_session_question_question_unique_per_session():
    session = QuizSessionFactory()
    question = QuestionFactory()
    SessionQuestionFactory(session=session, question=question, position=0)
    with pytest.raises(IntegrityError), transaction.atomic():
        SessionQuestionFactory(session=session, question=question, position=1)


def test_same_position_allowed_in_different_sessions():
    SessionQuestionFactory(position=0)
    SessionQuestionFactory(position=0)


def test_session_question_stores_choice_order_as_json():
    choices = ChoiceFactory.create_batch(4)
    ids = [c.id for c in reversed(choices)]
    sq = SessionQuestionFactory(choice_order=ids)
    sq.refresh_from_db()
    assert sq.choice_order == ids
    assert sq.result is None
    assert sq.points == 0


def test_inactive_question_default_active():
    assert Question.objects.filter(is_active=True).count() == 0
    QuestionFactory()
    assert Question.objects.filter(is_active=True).count() == 1
