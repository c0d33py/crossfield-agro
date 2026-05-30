from __future__ import annotations

from django.contrib.sitemaps import Sitemap

from apps.industries.selectors import get_active_industries


class IndustrySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def items(self):
        return get_active_industries().only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {"industries": IndustrySitemap}
