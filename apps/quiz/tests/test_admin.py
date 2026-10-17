import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.quiz.models import Choice, Question

from .factories import CategoryFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser("admin", "a@example.com", "pw-12345-test")
    client.force_login(user)
    return client


def payload(category, correct_flags):
    data = {
        "category": category.id,
        "text": "Test sorusu?",
        "difficulty": 2,
        "explanation": "",
        "is_active": "on",
        "choices-TOTAL_FORMS": len(correct_flags),
        "choices-INITIAL_FORMS": 0,
        "choices-MIN_NUM_FORMS": 0,
        "choices-MAX_NUM_FORMS": 4,
    }
    for i, correct in enumerate(correct_flags):
        data[f"choices-{i}-text"] = f"Şık {i}"
        if correct:
            data[f"choices-{i}-is_correct"] = "on"
    return data


def test_question_with_four_choices_one_correct_saves(admin_client):
    category = CategoryFactory()
    resp = admin_client.post(
        reverse("admin:quiz_question_add"), payload(category, [True, False, False, False])
    )
    assert resp.status_code == 302
    assert Question.objects.count() == 1
    assert Choice.objects.filter(is_correct=True).count() == 1


@pytest.mark.parametrize(
    "flags",
    [[False] * 4, [True, True, False, False], [True, False, False]],
    ids=["no-correct", "two-correct", "three-choices"],
)
def test_invalid_choice_sets_rejected(admin_client, flags):
    category = CategoryFactory()
    resp = admin_client.post(reverse("admin:quiz_question_add"), payload(category, flags))
    assert resp.status_code == 200
    assert Question.objects.count() == 0
