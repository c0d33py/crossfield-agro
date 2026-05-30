from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.utils import timezone

from apps.careers.models import JobPosting, PostingStatus


class JobPostingSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = "https"

    def items(self):
        # Direct query — the selector adds select_related which is incompatible with .only().
        now = timezone.now()
        return (
            JobPosting.objects.filter(
                status=PostingStatus.OPEN,
                published_at__lte=now,
            )
            .filter(Q(closes_at__isnull=True) | Q(closes_at__gt=now))
            .only("slug", "updated_at")
        )

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {"jobs": JobPostingSitemap}
