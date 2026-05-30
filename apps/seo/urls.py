from django.urls import path

from apps.seo import views

app_name = "seo"

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots"),
]
