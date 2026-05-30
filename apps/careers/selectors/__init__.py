from __future__ import annotations

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.careers.models import Department, JobPosting, PostingStatus


def get_open_postings() -> QuerySet[JobPosting]:
    now = timezone.now()
    return (
        JobPosting.objects.filter(
            status=PostingStatus.OPEN,
            published_at__lte=now,
        )
        .filter(Q(closes_at__isnull=True) | Q(closes_at__gt=now))
        .select_related("department")
        .order_by("-published_at")
    )


def get_posting_by_slug(slug: str) -> JobPosting | None:
    return JobPosting.objects.filter(slug=slug).select_related("department").first()


def get_postings_by_department() -> dict[str, list[JobPosting]]:
    grouped: dict[str, list[JobPosting]] = {}
    for posting in get_open_postings():
        grouped.setdefault(posting.department.name, []).append(posting)
    return grouped


def get_active_departments() -> QuerySet[Department]:
    return Department.objects.filter(is_active=True).order_by("position", "name")
