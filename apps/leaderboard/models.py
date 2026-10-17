from django.db import models


class ScoreEntry(models.Model):
    """Skor tablosu kaydı. Sıralama: puan↓, ortalama cevap süresi↑, kayıt zamanı↑."""

    session = models.OneToOneField(
        "quiz.QuizSession", on_delete=models.CASCADE, related_name="score_entry"
    )
    category = models.ForeignKey(
        "quiz.Category", on_delete=models.PROTECT, related_name="score_entries"
    )
    player_name = models.CharField(max_length=20)
    score = models.IntegerField()
    correct_count = models.PositiveSmallIntegerField()
    avg_response_ms = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "skor kaydı"
        verbose_name_plural = "skor kayıtları"
        indexes = [
            models.Index(
                fields=["category", "-score", "avg_response_ms", "created_at"],
                name="score_category_rank_idx",
            ),
            models.Index(
                fields=["-score", "avg_response_ms", "created_at"],
                name="score_global_rank_idx",
            ),
        ]
        ordering = ["-score", "avg_response_ms", "created_at"]

    def __str__(self):
        return f"{self.player_name}: {self.score}"
