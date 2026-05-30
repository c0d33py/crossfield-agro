from django.urls import path

from apps.industries import views

app_name = "industries"

urlpatterns = [
    path("", views.IndustryListView.as_view(), name="list"),
    path("<slug:slug>/", views.IndustryDetailView.as_view(), name="detail"),
]
