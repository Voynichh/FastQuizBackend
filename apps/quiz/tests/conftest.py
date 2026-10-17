import datetime as dt

import pytest
import time_machine
from django.core.cache import cache

from apps.quiz.models import Choice

from .factories import CategoryFactory, ChoiceFactory, QuestionFactory

POOL_SIZE = 25


def make_question(category, **kwargs):
    question = QuestionFactory(category=category, **kwargs)
    ChoiceFactory(question=question, is_correct=True)
    ChoiceFactory.create_batch(3, question=question)
    return question


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def category(db):
    category = CategoryFactory(slug="yapay-zeka", name="Yapay Zeka")
    for _ in range(POOL_SIZE):
        make_question(category)
    return category


@pytest.fixture
def clock():
    """Saati dondurur; clock.shift(timedelta) ile ilerletilir."""
    start = dt.datetime(2026, 10, 17, 8, 0, 0, tzinfo=dt.UTC)
    with time_machine.travel(start, tick=False) as traveller:
        yield traveller


def correct_choice_id(question_id):
    return Choice.objects.get(question_id=question_id, is_correct=True).id


def wrong_choice_id(question_id):
    return Choice.objects.filter(question_id=question_id, is_correct=False).first().id
