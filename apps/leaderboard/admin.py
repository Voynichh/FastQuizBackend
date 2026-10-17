from django.contrib import admin

from .models import ScoreEntry


@admin.register(ScoreEntry)
class ScoreEntryAdmin(admin.ModelAdmin):
    list_display = (
        "player_name",
        "score",
        "category",
        "correct_count",
        "avg_response_ms",
        "created_at",
    )
    list_filter = ("category",)
    search_fields = ("player_name",)
    readonly_fields = ("session", "created_at")
