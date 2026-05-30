from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from apps.media_center.models import MediaCoverage, PressRelease, ReleaseStatus


def get_published_releases() -> QuerySet[PressRelease]:
    today = timezone.now().date()
    return PressRelease.objects.filter(
        status=ReleaseStatus.PUBLISHED,
        issued_on__lte=today,
    ).order_by("-issued_on")


def get_release_by_slug(slug: str) -> PressRelease | None:
    return get_published_releases().filter(slug=slug).first()


def get_active_coverage() -> QuerySet[MediaCoverage]:
    return MediaCoverage.objects.filter(is_active=True).order_by("-published_on")


def get_featured_coverage(limit: int = 4) -> QuerySet[MediaCoverage]:
    return get_active_coverage().filter(is_featured=True)[:limit]
