from django.conf import settings
from django.db.models import Count, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common import exceptions as err
from apps.common.serializers import ErrorResponseSerializer

from . import serializers as s
from . import services
from .models import Category, QuizSession

SESSION_TOKEN = OpenApiParameter(
    "X-Session-Token",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=True,
    description="Oturum açılırken bir kez verilen gizli anahtar",
)
CLIENT = OpenApiParameter(
    "X-Client",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    enum=QuizSession.ClientType.values,
    description="İstemci türü (varsayılan: web)",
)


def errors(*codes: int) -> dict:
    return {code: ErrorResponseSerializer for code in codes}


def authenticated_session(request, session_id) -> QuizSession:
    return services.authenticate_session(session_id, request.headers.get("X-Session-Token"))


def client_type(request) -> str:
    value = request.headers.get("X-Client", QuizSession.ClientType.WEB).lower()
    if value not in QuizSession.ClientType.values:
        raise err.ValidationFailed(
            "Geçersiz istemci türü.",
            details={"X-Client": [f"Beklenen: {', '.join(QuizSession.ClientType.values)}"]},
        )
    return value


class CategoryListView(APIView):
    @extend_schema(
        operation_id="categories_list",
        summary="Aktif kategoriler",
        responses={200: s.CategoryListSerializer},
    )
    def get(self, request):
        categories = Category.objects.filter(is_active=True).annotate(
            question_count=Count("questions", filter=Q(questions__is_active=True))
        )
        return Response({"categories": s.CategorySerializer(categories, many=True).data})


class SessionCreateView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "session_create"

    @extend_schema(
        operation_id="sessions_create",
        summary="Yeni quiz oturumu aç",
        description=(
            "Kategoriden rastgele sorular seçer. `session_token` yalnızca bu yanıtta döner."
        ),
        parameters=[CLIENT],
        request=s.SessionCreateRequestSerializer,
        responses={201: s.SessionCreatedSerializer, **errors(400, 404, 409, 429)},
    )
    def post(self, request):
        data = s.SessionCreateRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        category = Category.objects.filter(
            slug=data.validated_data["category"], is_active=True
        ).first()
        if category is None:
            raise err.NotFound("Kategori bulunamadı.")
        session, token = services.create_session(category, client_type(request))
        body = {
            "session_id": session.id,
            "session_token": token,
            "category": category,
            "total_questions": session.session_questions.count(),
            "time_limit_ms": settings.QUIZ_TIME_LIMIT_MS,
        }
        return Response(s.SessionCreatedSerializer(body).data, status=status.HTTP_201_CREATED)


class CurrentQuestionView(APIView):
    @extend_schema(
        operation_id="sessions_current",
        summary="Sıradaki soru",
        description=(
            "Sıradaki soruyu verir ve süreyi başlatır. Aynı soru için tekrar çağrıda aynı "
            "`deadline` döner. Süresi geçmiş soru `timeout` olarak kapatılır. "
            "Doğru şık bu yanıtta asla yer almaz."
        ),
        parameters=[SESSION_TOKEN],
        responses={200: s.CurrentQuestionSerializer, **errors(401, 404, 409)},
    )
    def get(self, request, session_id):
        session = authenticated_session(request, session_id)
        current = services.get_current(session)
        body = {
            "position": current.position,
            "total_questions": current.total_questions,
            "question": {
                "id": current.question_id,
                "text": current.text,
                "choices": current.choices,
            },
            "time_limit_ms": current.time_limit_ms,
            "server_time": current.server_time,
            "deadline": current.deadline,
            "total_score": current.total_score,
        }
        return Response(s.CurrentQuestionSerializer(body).data)


class AnswerView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "answers"

    @extend_schema(
        operation_id="sessions_answer",
        summary="Aktif soruya cevap gönder",
        description="Süre dolduysa `choice_id: null` gönderilir. Puanı sunucu hesaplar.",
        parameters=[SESSION_TOKEN],
        request=s.AnswerRequestSerializer,
        responses={200: s.AnswerResultSerializer, **errors(400, 401, 404, 409, 429)},
    )
    def post(self, request, session_id):
        session = authenticated_session(request, session_id)
        data = s.AnswerRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result = services.submit_answer(
            session, data.validated_data["question_id"], data.validated_data["choice_id"]
        )
        return Response(s.AnswerResultSerializer(result).data)


class ResultView(APIView):
    @extend_schema(
        operation_id="sessions_result",
        summary="Oturum özeti ve tahmini sıralama",
        parameters=[SESSION_TOKEN],
        responses={200: s.SessionResultSerializer, **errors(401, 404, 409)},
    )
    def get(self, request, session_id):
        session = authenticated_session(request, session_id)
        result = services.get_result(session)
        body = {**result.__dict__, "status": QuizSession.Status.COMPLETED}
        return Response(s.SessionResultSerializer(body).data)


class ScoreView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "score"

    @extend_schema(
        operation_id="sessions_score",
        summary="Skoru skor tablosuna kaydet",
        description=(
            "Yalnızca `player_name` gönderilir; puan oturumdan okunur. Tamamlanmış bir oturum "
            "için en fazla bir kez kaydedilebilir."
        ),
        parameters=[SESSION_TOKEN],
        request=s.ScoreRequestSerializer,
        responses={201: s.ScoreSavedSerializer, **errors(400, 401, 404, 409, 429)},
    )
    def post(self, request, session_id):
        session = authenticated_session(request, session_id)
        data = s.ScoreRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        saved = services.save_score(session, data.validated_data["player_name"])
        return Response(s.ScoreSavedSerializer(saved).data, status=status.HTTP_201_CREATED)
