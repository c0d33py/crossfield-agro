from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import View

from apps.core.selectors import get_all_pages, get_page_meta, get_pages_by_section


class HomeView(View):
    template_name = "core/pages/home.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"is_home": True})


# Legacy core slugs that have moved to dedicated apps. We 301-redirect so external
# links and search indexes don't break. Add an entry whenever a core page moves.
LEGACY_REDIRECTS = {
    "contact-us": "contact:form",
    "careers": "careers:list",
    "industries": "industries:list",
    "services": "services:list",
}


class PageView(View):
    """
    Generic corporate page dispatcher. Slug -> registry -> per-page template.
    Special slugs (site-map) delegate to a dedicated view.
    Legacy slugs (contact-us, careers, etc.) 301-redirect to their new homes.
    If the per-page template is missing we 404.
    """

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        if slug in LEGACY_REDIRECTS:
            return HttpResponsePermanentRedirect(reverse(LEGACY_REDIRECTS[slug]))
        if slug == "site-map":
            return SiteMapPageView.as_view()(request)

        page = get_page_meta(slug)
        if page is None:
            raise Http404("Page not found")
        try:
            get_template(page.template)
        except TemplateDoesNotExist:
            raise Http404("Page not yet published")
        return render(request, page.template, {"page": page})


class SiteMapPageView(View):
    template_name = "core/pages/site_map.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        page = get_page_meta("site-map")
        return render(
            request,
            self.template_name,
            {"page": page, "sections": get_pages_by_section(), "all_pages": get_all_pages()},
        )
