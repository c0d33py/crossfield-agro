from django.urls import path

from apps.careers import views

app_name = "careers"

urlpatterns = [
    path("", views.CareersListView.as_view(), name="list"),
    path("<slug:slug>/", views.CareersDetailView.as_view(), name="detail"),
]
