from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.utils import timezone

from apps.blog.models import Author, Post, PostStatus, Tag


class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    protocol = "https"

    def items(self):
        return Post.objects.filter(
            status=PostStatus.PUBLISHED,
            published_at__lte=timezone.now(),
        ).only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


class TagSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5
    protocol = "https"

    def items(self):
        return Tag.objects.all().only("slug")


class AuthorSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4
    protocol = "https"

    def items(self):
        return Author.objects.filter(is_active=True).only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "blog-posts": PostSitemap,
    "blog-tags": TagSitemap,
    "blog-authors": AuthorSitemap,
}
