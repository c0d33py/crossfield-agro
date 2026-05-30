from django.urls import path

from apps.blog import views

app_name = "blog"

urlpatterns = [
    path("", views.PostListView.as_view(), name="list"),
    path("tag/<slug:slug>/", views.TagDetailView.as_view(), name="tag-detail"),
    path("author/<slug:slug>/", views.AuthorDetailView.as_view(), name="author-detail"),
    path("<slug:slug>/", views.PostDetailView.as_view(), name="post-detail"),
]
