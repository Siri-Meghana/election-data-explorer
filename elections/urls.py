from django.urls import path

from . import views

app_name = "elections"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("candidates/", views.CandidateListView.as_view(), name="candidate_list"),
    path(
        "candidates/<str:candidate_id>/",
        views.CandidateDetailView.as_view(),
        name="candidate_detail",
    ),
]
