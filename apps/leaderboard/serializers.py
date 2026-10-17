from rest_framework import serializers

from apps.common.fields import UtcMillisDateTimeField


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    player_name = serializers.CharField()
    score = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    avg_response_ms = serializers.IntegerField()
    created_at = UtcMillisDateTimeField()


class LeaderboardSerializer(serializers.Serializer):
    category = serializers.CharField(allow_null=True, help_text="Kategori slug'ı; genel için null")
    entries = LeaderboardEntrySerializer(many=True)
