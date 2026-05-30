from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from apps.industries.models import Industry
from apps.products.models import Product, ProductStatus


def get_active_industries() -> QuerySet[Industry]:
    return Industry.objects.filter(is_active=True).order_by("position", "name")


def get_industry_by_slug(slug: str) -> Industry | None:
    return Industry.objects.filter(slug=slug, is_active=True).first()


def get_products_for_industry(industry: Industry) -> QuerySet[Product]:
    """Published products linked to this industry via the M2M."""
    return (
        Product.objects.filter(
            industries=industry,
            status=ProductStatus.PUBLISHED,
            published_at__lte=timezone.now(),
        )
        .select_related("category")
        .prefetch_related("images")
        .order_by("-published_at")
    )
