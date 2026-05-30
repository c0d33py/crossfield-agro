from __future__ import annotations

from django.contrib.sitemaps import Sitemap

from apps.media_center.selectors import get_published_releases


class PressReleaseSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5
    protocol = "https"

    def items(self):
        return get_published_releases().only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {"press-releases": PressReleaseSitemap}
