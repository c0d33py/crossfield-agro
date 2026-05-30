from __future__ import annotations

from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.generic import View

from apps.blog.selectors import (
    get_all_tags,
    get_author_by_slug,
    get_post_by_slug,
    get_posts_for_author,
    get_posts_for_tag,
    get_published_posts,
    get_related_posts,
    get_tag_by_slug,
)


class PostListView(View):
    template_name = "blog/post_list.html"
    paginate_by = 9

    def get(self, request: HttpRequest) -> HttpResponse:
        qs = get_published_posts()
        page = Paginator(qs, self.paginate_by).get_page(request.GET.get("page"))
        return render(
            request,
            self.template_name,
            {
                "page_obj": page,
                "posts": page.object_list,
                "tags": get_all_tags(),
            },
        )


class PostDetailView(View):
    template_name = "blog/post_detail.html"

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        post = get_post_by_slug(slug)
        if post is None:
            raise Http404("Post not found")
        return render(
            request,
            self.template_name,
            {
                "post": post,
                "related": get_related_posts(post),
            },
        )


class TagDetailView(View):
    template_name = "blog/tag_detail.html"
    paginate_by = 9

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        tag = get_tag_by_slug(slug)
        if tag is None:
            raise Http404("Tag not found")
        page = Paginator(get_posts_for_tag(tag), self.paginate_by).get_page(request.GET.get("page"))
        return render(
            request,
            self.template_name,
            {
                "tag": tag,
                "page_obj": page,
                "posts": page.object_list,
            },
        )


class AuthorDetailView(View):
    template_name = "blog/author_detail.html"
    paginate_by = 9

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        author = get_author_by_slug(slug)
        if author is None:
            raise Http404("Author not found")
        page = Paginator(get_posts_for_author(author), self.paginate_by).get_page(
            request.GET.get("page")
        )
        return render(
            request,
            self.template_name,
            {
                "author": author,
                "page_obj": page,
                "posts": page.object_list,
            },
        )
