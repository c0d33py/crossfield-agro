from django.urls import path

from apps.orders import views

app_name = "orders"

urlpatterns = [
    path("", views.OrderListView.as_view(), name="list"),
    path("track/", views.OrderTrackView.as_view(), name="track"),
    path("track/<str:order_number>/", views.OrderTrackDetailView.as_view(), name="track-detail"),
    path("<uuid:order_uuid>/", views.OrderDetailView.as_view(), name="detail"),
    path(
        "<uuid:order_uuid>/confirmation/",
        views.OrderConfirmationView.as_view(),
        name="confirmation",
    ),
    path("<uuid:order_uuid>/status/", views.OrderStatusView.as_view(), name="status"),
]
