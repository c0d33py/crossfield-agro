from django.urls import path

from apps.products import views

app_name = "products"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product-list"),
    path("search/", views.ProductSearchView.as_view(), name="product-search"),
    path(
        "category/<slug:slug>/",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path("<slug:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
]
