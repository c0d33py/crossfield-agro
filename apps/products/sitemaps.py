from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.utils import timezone

from apps.products.models import Category, Product, ProductStatus


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        # Direct query — sitemap doesn't need the prefetches the selector adds.
        return Product.objects.filter(
            status=ProductStatus.PUBLISHED,
            published_at__lte=timezone.now(),
        ).only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return Category.objects.filter(is_active=True).only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "products": ProductSitemap,
    "product-categories": CategorySitemap,
}
