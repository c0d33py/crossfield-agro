from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.products.models import Product, ProductVariant
from apps.products.validators import (
    validate_price,
    validate_sku,
    validate_stock_quantity,
)


@transaction.atomic
def create_variant(
    *,
    product: Product,
    name: str,
    sku: str,
    unit_price: Decimal,
    stock_quantity: int = 0,
    attributes: dict | None = None,
    weight_kg: Decimal | None = None,
    position: int = 0,
) -> ProductVariant:
    validate_sku(sku)
    validate_price(unit_price)
    validate_stock_quantity(stock_quantity)

    return ProductVariant.objects.create(
        product=product,
        name=name,
        sku=sku,
        unit_price=unit_price,
        stock_quantity=stock_quantity,
        attributes=attributes or {},
        weight_kg=weight_kg,
        position=position,
    )


@transaction.atomic
def update_variant(*, variant: ProductVariant, **fields) -> ProductVariant:
    if "unit_price" in fields:
        validate_price(fields["unit_price"])
    if "sku" in fields:
        validate_sku(fields["sku"])
    if "stock_quantity" in fields:
        validate_stock_quantity(fields["stock_quantity"])
    for k, v in fields.items():
        setattr(variant, k, v)
    variant.save(update_fields=list(fields.keys()) + ["updated_at"])
    return variant


@transaction.atomic
def archive_variant(*, variant: ProductVariant) -> ProductVariant:
    variant.is_active = False
    variant.save(update_fields=["is_active", "updated_at"])
    return variant
