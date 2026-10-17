import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class Category(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, help_text="İkon adı (web ve mobil aynı seti kullanır)")
    color = models.CharField(max_length=20, help_text="Tema token adı, ör. cat-ai")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "kategori"
        verbose_name_plural = "kategoriler"

    def __str__(self):
        return self.name


class Question(models.Model):
    class Difficulty(models.IntegerChoices):
        EASY = 1, "Kolay"
        MEDIUM = 2, "Orta"
        HARD = 3, "Zor"

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="questions")
    text = models.CharField(max_length=300, help_text="5 saniyede okunabilmesi için kısa tutulur")
    difficulty = models.PositiveSmallIntegerField(
        choices=Difficulty.choices, default=Difficulty.MEDIUM
    )
    explanation = models.TextField(null=True, blank=True)  # noqa: DJ001
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "soru"
        verbose_name_plural = "sorular"
        constraints = [
            models.CheckConstraint(
                condition=Q(difficulty__gte=1, difficulty__lte=3),
                name="question_difficulty_1_to_3",
            ),
        ]

    def __str__(self):
        return self.text[:60]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=120)
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = "şık"
        verbose_name_plural = "şıklar"
        constraints = [
            models.UniqueConstraint(
                fields=["question"],
                condition=Q(is_correct=True),
                name="choice_one_correct_per_question",
            ),
        ]

    def __str__(self):
        return self.text


class QuizSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktif"
        COMPLETED = "completed", "Tamamlandı"
        ABANDONED = "abandoned", "Terk edildi"

    class ClientType(models.TextChoices):
        WEB = "web", "Web"
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(
        max_length=64, help_text="İstemciye bir kez verilen anahtarın SHA-256 özeti"
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="sessions")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    client_type = models.CharField(
        max_length=10, choices=ClientType.choices, default=ClientType.WEB
    )
    current_index = models.PositiveSmallIntegerField(default=0)
    total_score = models.IntegerField(default=0)
    correct_count = models.IntegerField(default=0)
    wrong_count = models.IntegerField(default=0)
    empty_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(
        default=timezone.now, help_text="Hareketsizlik (abandoned) kontrolü için"
    )

    class Meta:
        verbose_name = "quiz oturumu"
        verbose_name_plural = "quiz oturumları"

    def __str__(self):
        return f"{self.id} ({self.status})"


class SessionQuestion(models.Model):
    class Result(models.TextChoices):
        CORRECT = "correct", "Doğru"
        WRONG = "wrong", "Yanlış"
        TIMEOUT = "timeout", "Süre aşımı"

    session = models.ForeignKey(
        QuizSession, on_delete=models.CASCADE, related_name="session_questions"
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="+")
    position = models.PositiveSmallIntegerField()
    choice_order = models.JSONField(help_text="Karıştırılmış şık id sırası")
    served_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    selected_choice = models.ForeignKey(
        Choice, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    result = models.CharField(max_length=10, choices=Result.choices, null=True, blank=True)  # noqa: DJ001
    response_ms = models.IntegerField(null=True, blank=True)
    points = models.IntegerField(default=0)

    class Meta:
        verbose_name = "oturum sorusu"
        verbose_name_plural = "oturum soruları"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "position"], name="sessionquestion_unique_position"
            ),
            models.UniqueConstraint(
                fields=["session", "question"], name="sessionquestion_unique_question"
            ),
        ]
        ordering = ["session_id", "position"]

    def __str__(self):
        return f"{self.session_id}#{self.position}"
