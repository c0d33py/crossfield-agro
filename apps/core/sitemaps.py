"""Sitemap for static corporate pages registered in apps.core.selectors.pages."""

from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import reverse

from apps.core.selectors import PAGE_REGISTRY


class CorporatePagesSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https"

    def items(self):
        # Only emit pages whose template actually exists. Otherwise the
        # PageView would 404 and we'd be advertising broken URLs to search.
        out = []
        for page in PAGE_REGISTRY.values():
            try:
                get_template(page.template)
            except TemplateDoesNotExist:
                continue
            out.append(page)
        return out

    def location(self, item):
        return reverse("core:page", kwargs={"slug": item.slug})


class HomeSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0
    protocol = "https"

    def items(self):
        return ["home"]

    def location(self, item):
        return reverse("core:home")


sitemaps = {
    "home": HomeSitemap,
    "corporate": CorporatePagesSitemap,
}
