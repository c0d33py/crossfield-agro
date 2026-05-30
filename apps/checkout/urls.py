from django.urls import path

from apps.checkout import views

app_name = "checkout"

urlpatterns = [
    path("", views.CheckoutStartView.as_view(), name="start"),
    path("address/", views.AddressView.as_view(), name="address"),
    path("review/", views.ReviewView.as_view(), name="review"),
    path("payment/", views.PaymentView.as_view(), name="payment"),
    path("return/<uuid:order_uuid>/", views.CheckoutReturnView.as_view(), name="return"),
]
