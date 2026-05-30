from __future__ import annotations

from django.db.models import QuerySet

from apps.services.models import ServiceCategory, ServiceOffering


def get_active_offerings() -> QuerySet[ServiceOffering]:
    return ServiceOffering.objects.filter(is_active=True).order_by("position", "name")


def get_offering_by_slug(slug: str) -> ServiceOffering | None:
    return ServiceOffering.objects.filter(slug=slug, is_active=True).first()


def get_offerings_by_category() -> dict[str, list[ServiceOffering]]:
    """Group active offerings by their category for the list page."""
    grouped: dict[str, list[ServiceOffering]] = {}
    for offering in get_active_offerings():
        label = ServiceCategory(offering.category).label
        grouped.setdefault(label, []).append(offering)
    return grouped
