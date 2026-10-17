from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

handler404 = "apps.common.views.not_found"
handler500 = "apps.common.views.server_error"

# /api/v1/health/ HealthCheckMiddleware tarafından yanıtlanır.
api_v1 = [
    path("", include("apps.quiz.urls")),
    path("", include("apps.leaderboard.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

urlpatterns = [
    path("api/v1/", include(api_v1)),
]
