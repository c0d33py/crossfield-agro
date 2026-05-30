from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone

from apps.products.models import Category, Product, ProductImage, ProductStatus, ProductVariant


def _base_published_qs() -> QuerySet[Product]:
    now = timezone.now()
    return (
        Product.objects.filter(
            status=ProductStatus.PUBLISHED,
            published_at__lte=now,
        )
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ProductImage.objects.order_by("position", "id"),
            ),
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.filter(is_active=True).order_by("position"),
            ),
        )
    )


SORT_CHOICES = {
    "newest": "-published_at",
    "name": "name",
    "price-asc": "unit_price",
    "price-desc": "-unit_price",
}


def get_published_products(
    *,
    category_id: int | None = None,
    sort: str | None = None,
) -> QuerySet[Product]:
    qs = _base_published_qs()
    if category_id:
        qs = qs.filter(category_id=category_id)
    order = SORT_CHOICES.get(sort or "newest", SORT_CHOICES["newest"])
    return qs.order_by(order, "-id")


def get_product_by_slug(slug: str) -> Product | None:
    return _base_published_qs().filter(slug=slug).first()


def get_products_for_category(category: Category) -> QuerySet[Product]:
    """Includes products in this category AND any of its descendant categories."""
    descendant_ids = _collect_descendant_ids(category)
    return _base_published_qs().filter(category_id__in=descendant_ids)


def get_related_products(product: Product, limit: int = 4) -> QuerySet[Product]:
    return (
        _base_published_qs().filter(category_id=product.category_id).exclude(pk=product.pk)[:limit]
    )


def search_products(query: str) -> QuerySet[Product]:
    q = (query or "").strip()
    if not q:
        return _base_published_qs().none()
    return _base_published_qs().filter(
        Q(name__icontains=q)
        | Q(sku__iexact=q)
        | Q(short_description__icontains=q)
        | Q(description__icontains=q)
    )


def _collect_descendant_ids(category: Category) -> list[int]:
    ids = [category.pk]
    frontier = [category.pk]
    while frontier:
        children = list(
            Category.objects.filter(parent_id__in=frontier, is_active=True).values_list(
                "id", flat=True
            )
        )
        if not children:
            break
        ids.extend(children)
        frontier = children
    return ids
