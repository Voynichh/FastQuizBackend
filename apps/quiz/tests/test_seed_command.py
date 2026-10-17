import pytest
from django.core.management import call_command

from apps.quiz.models import Category, Question

pytestmark = pytest.mark.django_db


def run(*args):
    call_command("seed_questions", *args, verbosity=0)


def test_seeds_empty_database():
    run()
    assert Category.objects.count() == 5
    assert Question.objects.count() == 200


def test_skips_when_data_exists_so_existing_data_survives():
    run()
    question = Question.objects.first()
    question.text = "El ile düzenlendi"
    question.save()
    run()
    question.refresh_from_db()
    assert question.text == "El ile düzenlendi"


def test_force_reloads_fixture_data():
    run()
    question = Question.objects.first()
    question.text = "El ile düzenlendi"
    question.save()
    run("--force")
    question.refresh_from_db()
    assert question.text != "El ile düzenlendi"
    assert Question.objects.count() == 200
