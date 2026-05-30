from django.urls import path

from apps.services import views

app_name = "services"

urlpatterns = [
    path("", views.ServiceListView.as_view(), name="list"),
    path("<slug:slug>/", views.ServiceDetailView.as_view(), name="detail"),
]
