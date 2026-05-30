from __future__ import annotations

from django.contrib.sitemaps import Sitemap

from apps.services.selectors import get_active_offerings


class ServiceOfferingSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return get_active_offerings().only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {"services": ServiceOfferingSitemap}
