from rest_framework import serializers

from apps.common.fields import UtcMillisDateTimeField

from .models import Category, QuizSession


class CategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["slug", "name", "icon", "color"]


class CategorySerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(help_text="Havuzdaki aktif soru sayısı")

    class Meta:
        model = Category
        fields = ["slug", "name", "description", "icon", "color", "question_count"]


class CategoryListSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True)


class SessionCreateRequestSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=50, help_text="Kategori slug'ı")


class SessionCreatedSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    session_token = serializers.CharField(
        help_text="Yalnızca bu yanıtta döner; istemci saklar ve X-Session-Token ile gönderir"
    )
    category = CategoryBriefSerializer()
    total_questions = serializers.IntegerField()
    time_limit_ms = serializers.IntegerField()


class ChoiceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()


class QuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    choices = ChoiceSerializer(many=True)


class CurrentQuestionSerializer(serializers.Serializer):
    position = serializers.IntegerField(help_text="0 tabanlı sıra")
    total_questions = serializers.IntegerField()
    question = QuestionSerializer()
    time_limit_ms = serializers.IntegerField()
    server_time = UtcMillisDateTimeField(help_text="Sunucu saati; sayaç farkını düzeltmek için")
    deadline = UtcMillisDateTimeField()
    total_score = serializers.IntegerField()


class AnswerRequestSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    choice_id = serializers.IntegerField(allow_null=True, help_text="Süre dolduysa null gönderilir")


class AnswerResultSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=["correct", "wrong", "timeout"])
    correct_choice_id = serializers.IntegerField()
    points = serializers.IntegerField()
    response_ms = serializers.IntegerField(help_text="Sunucunun ölçtüğü süre")
    total_score = serializers.IntegerField()
    is_last = serializers.BooleanField()


class SessionResultSerializer(serializers.Serializer):
    category = CategoryBriefSerializer()
    status = serializers.ChoiceField(choices=QuizSession.Status.values, required=False)
    total_questions = serializers.IntegerField()
    total_score = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    wrong_count = serializers.IntegerField()
    empty_count = serializers.IntegerField()
    avg_response_ms = serializers.IntegerField()
    estimated_rank = serializers.IntegerField(
        help_text="Kategori skor tablosundaki tahmini (kaydedildiyse gerçek) sıra"
    )
    in_top_10 = serializers.BooleanField()
    score_saved = serializers.BooleanField()


class ScoreRequestSerializer(serializers.Serializer):
    # Uzunluk/karakter/küfür denetimi tek yerde (leaderboard.services) yapılır.
    player_name = serializers.CharField(max_length=100, allow_blank=True, trim_whitespace=False)


class ScoreSavedSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    in_top_10 = serializers.BooleanField()
    score = serializers.IntegerField()
