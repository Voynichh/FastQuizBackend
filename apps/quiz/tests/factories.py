import hashlib
import secrets

import factory

from apps.quiz.models import Category, Choice, Question, QuizSession, SessionQuestion


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    slug = factory.Sequence(lambda n: f"kategori-{n}")
    name = factory.Sequence(lambda n: f"Kategori {n}")
    description = "Açıklama"
    icon = "code"
    color = "cat-software"
    order = factory.Sequence(lambda n: n)


class QuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Question

    category = factory.SubFactory(CategoryFactory)
    text = factory.Sequence(lambda n: f"Soru {n}?")
    difficulty = Question.Difficulty.MEDIUM


class ChoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Choice

    question = factory.SubFactory(QuestionFactory)
    text = factory.Sequence(lambda n: f"Şık {n}")
    is_correct = False


class QuizSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = QuizSession

    category = factory.SubFactory(CategoryFactory)
    token_hash = factory.LazyFunction(lambda: hashlib.sha256(secrets.token_bytes(32)).hexdigest())


class SessionQuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SessionQuestion

    session = factory.SubFactory(QuizSessionFactory)
    question = factory.SubFactory(QuestionFactory)
    position = factory.Sequence(lambda n: n)
    choice_order = factory.LazyFunction(list)
