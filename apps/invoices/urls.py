from django.urls import path

from apps.invoices import views

app_name = "invoices"

urlpatterns = [
    path("<str:number>/", views.InvoiceDownloadView.as_view(), name="download"),
]
