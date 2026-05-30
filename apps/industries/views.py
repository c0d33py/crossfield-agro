from __future__ import annotations

from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.generic import View

from apps.industries.selectors import (
    get_active_industries,
    get_industry_by_slug,
    get_products_for_industry,
)


class IndustryListView(View):
    template_name = "industries/industry_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {"industries": get_active_industries()},
        )


class IndustryDetailView(View):
    template_name = "industries/industry_detail.html"
    paginate_by = 12

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        industry = get_industry_by_slug(slug)
        if industry is None:
            raise Http404("Industry not found")
        page = Paginator(get_products_for_industry(industry), self.paginate_by).get_page(
            request.GET.get("page")
        )
        return render(
            request,
            self.template_name,
            {"industry": industry, "page_obj": page, "products": page.object_list},
        )
