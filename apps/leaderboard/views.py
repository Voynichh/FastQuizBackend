from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import exceptions as err
from apps.common.serializers import ErrorResponseSerializer
from apps.quiz.models import Category

from . import services
from .serializers import LeaderboardSerializer


class LeaderboardView(APIView):
    @extend_schema(
        operation_id="leaderboard_list",
        summary="Skor tablosu (ilk 10)",
        description="`category` verilmezse tüm kategorilerin genel tablosu döner.",
        parameters=[
            OpenApiParameter("category", str, description="Kategori slug'ı (opsiyonel)"),
        ],
        responses={200: LeaderboardSerializer, 404: ErrorResponseSerializer},
    )
    def get(self, request):
        slug = request.query_params.get("category")
        category = None
        if slug:
            category = Category.objects.filter(slug=slug, is_active=True).first()
            if category is None:
                raise err.NotFound("Kategori bulunamadı.")
        entries = services.top_entries(category)
        return Response(
            LeaderboardSerializer(
                {"category": category.slug if category else None, "entries": entries}
            ).data
        )
