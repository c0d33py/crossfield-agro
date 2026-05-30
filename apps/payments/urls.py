from django.urls import path

from apps.payments import views

app_name = "payments"

urlpatterns = [
    path("webhook/<str:gateway_name>/", views.payment_webhook, name="webhook"),
]
