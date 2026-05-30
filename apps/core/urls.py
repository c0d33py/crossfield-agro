from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("<slug:slug>/", views.PageView.as_view(), name="page"),
]
