from django.urls import path

from apps.media_center import views

app_name = "media_center"

urlpatterns = [
    path("", views.MediaIndexView.as_view(), name="index"),
    path("press-releases/", views.PressReleaseListView.as_view(), name="press-list"),
    path(
        "press-releases/<slug:slug>/", views.PressReleaseDetailView.as_view(), name="press-detail"
    ),
    path("coverage/", views.CoverageListView.as_view(), name="coverage-list"),
]
