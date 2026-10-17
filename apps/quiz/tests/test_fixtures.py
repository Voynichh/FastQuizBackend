from collections import Counter

import pytest
from django.core.management import call_command

from apps.quiz.models import Category, Choice, Question

pytestmark = pytest.mark.django_db

MIN_QUESTIONS_PER_CATEGORY = 40
FIXTURE_FILES = [
    "fixtures/categories.json",
    "fixtures/questions_yazilim.json",
    "fixtures/questions_bilgisayar-muhendisligi.json",
    "fixtures/questions_yapay-zeka.json",
    "fixtures/questions_ulkeler.json",
    "fixtures/questions_fizik.json",
]


@pytest.fixture
def loaded():
    call_command("loaddata", *FIXTURE_FILES, verbosity=0)


def test_five_categories_loaded(loaded):
    assert set(Category.objects.values_list("slug", flat=True)) == {
        "yazilim",
        "bilgisayar-muhendisligi",
        "yapay-zeka",
        "ulkeler",
        "fizik",
    }


def test_each_category_has_enough_questions(loaded):
    for category in Category.objects.all():
        count = Question.objects.filter(category=category, is_active=True).count()
        assert count >= MIN_QUESTIONS_PER_CATEGORY, f"{category.slug}: {count}"


def test_every_question_has_four_distinct_choices_and_one_correct(loaded):
    for question in Question.objects.prefetch_related("choices"):
        choices = list(question.choices.all())
        assert len(choices) == 4, question.text
        assert sum(c.is_correct for c in choices) == 1, question.text
        assert len({c.text.strip().lower() for c in choices}) == 4, question.text


def test_question_texts_unique_within_category(loaded):
    pairs = Question.objects.values_list("category_id", "text")
    duplicates = [pair for pair, n in Counter(pairs).items() if n > 1]
    assert not duplicates


def test_lengths_and_difficulty_within_limits(loaded):
    assert all(len(q.text) <= 300 for q in Question.objects.all())
    assert all(len(c.text) <= 120 for c in Choice.objects.all())
    assert set(Question.objects.values_list("difficulty", flat=True)) <= {1, 2, 3}


def test_loaddata_is_idempotent(loaded):
    before = (Question.objects.count(), Choice.objects.count())
    call_command("loaddata", *FIXTURE_FILES, verbosity=0)
    assert (Question.objects.count(), Choice.objects.count()) == before
