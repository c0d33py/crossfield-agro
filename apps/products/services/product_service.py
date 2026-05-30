from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.products.models import Category, Product, ProductImage, ProductStatus
from apps.products.validators import (
    validate_order_quantity_bounds,
    validate_price,
    validate_seo_description,
    validate_seo_title,
    validate_sku,
    validate_stock_quantity,
)

User = get_user_model()


@transaction.atomic
def create_product(
    *,
    name: str,
    sku: str,
    category: Category,
    unit_price: Decimal,
    short_description: str = "",
    description: str = "",
    specifications: dict | None = None,
    currency: str = "PKR",
    track_inventory: bool = True,
    stock_quantity: int = 0,
    allow_backorder: bool = False,
    min_order_quantity: int = 1,
    max_order_quantity: int | None = None,
    weight_kg: Decimal | None = None,
    seo_title: str = "",
    seo_description: str = "",
    created_by: User | None = None,
) -> Product:
    validate_sku(sku)
    validate_price(unit_price)
    validate_stock_quantity(stock_quantity)
    validate_order_quantity_bounds(min_qty=min_order_quantity, max_qty=max_order_quantity)
    validate_seo_title(seo_title)
    validate_seo_description(seo_description)

    return Product.objects.create(
        name=name,
        slug=_unique_slug(Product, slugify(name)),
        sku=sku,
        category=category,
        short_description=short_description,
        description=description,
        specifications=specifications or {},
        unit_price=unit_price,
        currency=currency,
        track_inventory=track_inventory,
        stock_quantity=stock_quantity,
        allow_backorder=allow_backorder,
        min_order_quantity=min_order_quantity,
        max_order_quantity=max_order_quantity,
        weight_kg=weight_kg,
        seo_title=seo_title,
        seo_description=seo_description,
        created_by=created_by,
        status=ProductStatus.DRAFT,
    )


@transaction.atomic
def update_product(*, product: Product, **fields) -> Product:
    if "unit_price" in fields:
        validate_price(fields["unit_price"])
    if "sku" in fields:
        validate_sku(fields["sku"])
    if "stock_quantity" in fields:
        validate_stock_quantity(fields["stock_quantity"])
    if "min_order_quantity" in fields or "max_order_quantity" in fields:
        validate_order_quantity_bounds(
            min_qty=fields.get("min_order_quantity", product.min_order_quantity),
            max_qty=fields.get("max_order_quantity", product.max_order_quantity),
        )
    if "seo_title" in fields:
        validate_seo_title(fields["seo_title"])
    if "seo_description" in fields:
        validate_seo_description(fields["seo_description"])

    for k, v in fields.items():
        setattr(product, k, v)
    product.save(update_fields=list(fields.keys()) + ["updated_at"])
    return product


@transaction.atomic
def publish_product(*, product: Product) -> Product:
    if not product.images.exists():
        from django.core.exceptions import ValidationError

        raise ValidationError("Product must have at least one image before publishing.")
    product.status = ProductStatus.PUBLISHED
    if product.published_at is None:
        product.published_at = timezone.now()
    product.save(update_fields=["status", "published_at", "updated_at"])
    return product


@transaction.atomic
def archive_product(*, product: Product) -> Product:
    product.status = ProductStatus.ARCHIVED
    product.save(update_fields=["status", "updated_at"])
    return product


@transaction.atomic
def add_product_image(
    *,
    product: Product,
    image,
    alt_text: str = "",
    position: int | None = None,
    is_primary: bool = False,
) -> ProductImage:
    if position is None:
        last = product.images.order_by("-position").first()
        position = (last.position + 1) if last else 0

    if is_primary:
        product.images.filter(is_primary=True).update(is_primary=False)

    return ProductImage.objects.create(
        product=product,
        image=image,
        alt_text=alt_text,
        position=position,
        is_primary=is_primary,
    )


@transaction.atomic
def reorder_product_images(*, product: Product, ordered_image_ids: Iterable[int]) -> None:
    ids = list(ordered_image_ids)
    existing = {img.id: img for img in product.images.all()}
    for position, image_id in enumerate(ids):
        img = existing.get(image_id)
        if img is None:
            continue
        if img.position != position:
            img.position = position
            img.save(update_fields=["position"])


def _unique_slug(model, base: str) -> str:
    slug = base or "item"
    candidate = slug
    n = 2
    while model.objects.filter(slug=candidate).exists():
        candidate = f"{slug}-{n}"
        n += 1
    return candidate
