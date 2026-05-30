from __future__ import annotations

from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.generic import View

from apps.media_center.selectors import (
    get_active_coverage,
    get_published_releases,
    get_release_by_slug,
)


class MediaIndexView(View):
    template_name = "media_center/index.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {
                "releases": get_published_releases()[:6],
                "coverage": get_active_coverage()[:6],
            },
        )


class PressReleaseListView(View):
    template_name = "media_center/press_list.html"
    paginate_by = 12

    def get(self, request: HttpRequest) -> HttpResponse:
        page = Paginator(get_published_releases(), self.paginate_by).get_page(
            request.GET.get("page")
        )
        return render(request, self.template_name, {"page_obj": page, "releases": page.object_list})


class PressReleaseDetailView(View):
    template_name = "media_center/press_detail.html"

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        release = get_release_by_slug(slug)
        if release is None:
            raise Http404("Press release not found")
        return render(request, self.template_name, {"release": release})


class CoverageListView(View):
    template_name = "media_center/coverage_list.html"
    paginate_by = 20

    def get(self, request: HttpRequest) -> HttpResponse:
        page = Paginator(get_active_coverage(), self.paginate_by).get_page(request.GET.get("page"))
        return render(request, self.template_name, {"page_obj": page, "coverage": page.object_list})
