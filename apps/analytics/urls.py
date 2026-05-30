from django.urls import path

from apps.analytics import views

app_name = "analytics"

urlpatterns = [
    path("pageview/", views.pageview, name="pageview"),
    path("event/", views.event, name="event"),
]
