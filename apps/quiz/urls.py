from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("sessions/", views.SessionCreateView.as_view(), name="session-create"),
    path(
        "sessions/<uuid:session_id>/current/",
        views.CurrentQuestionView.as_view(),
        name="session-current",
    ),
    path("sessions/<uuid:session_id>/answers/", views.AnswerView.as_view(), name="session-answer"),
    path("sessions/<uuid:session_id>/result/", views.ResultView.as_view(), name="session-result"),
    path("sessions/<uuid:session_id>/score/", views.ScoreView.as_view(), name="session-score"),
]
