"""
Inventory writes — single entry point for stock decrement on PAID transition.

Per .claude/rules/commerce-rules.md:
  - Stock decrement happens at payment confirmation, not at cart-add or order-create.
  - Negative stock is impossible — use DB-level constraint (PositiveIntegerField).
  - Overselling: explicit business decision per product (allow_backorder).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction
from django.db.models import F

from apps.products.models import Product, ProductVariant

logger = logging.getLogger(__name__)


class InsufficientStock(Exception):
    """Raised when a decrement would push stock below zero on a non-backorder product."""


@dataclass(frozen=True)
class StockChange:
    product_id: int
    variant_id: int | None
    quantity: int
    sku: str


@transaction.atomic
def decrement_stock_for_order(*, order) -> list[StockChange]:
    """
    Atomically decrement stock for every line on an order. Uses SELECT FOR UPDATE
    to prevent race conditions, and F() expressions to avoid lost updates.

    Returns the list of decrements applied (for audit). Raises InsufficientStock
    if any line cannot be fulfilled (and the whole transaction rolls back).
    """
    applied: list[StockChange] = []

    for item in order.items.select_related("product", "variant").all():
        target_model = ProductVariant if item.variant_id else Product
        target_id = item.variant_id if item.variant_id else item.product_id

        # Lock the row so concurrent orders can't oversell
        row = target_model.objects.select_for_update().get(pk=target_id)

        # If the parent product allows backorder, skip the stock check entirely
        allow_backorder = (
            item.product.allow_backorder
            if not item.variant_id
            else item.product.allow_backorder  # variants inherit parent backorder policy
        )
        track_inventory = item.product.track_inventory

        if track_inventory and not allow_backorder and row.stock_quantity < item.quantity:
            raise InsufficientStock(
                f"Insufficient stock for {item.sku}: have {row.stock_quantity}, need {item.quantity}"
            )

        if track_inventory:
            # Cap the decrement so PositiveIntegerField never goes negative even
            # under backorder. If allow_backorder is True and stock < requested,
            # we deplete to zero and let ops handle the shortfall (out-of-band).
            decrement_by = min(item.quantity, row.stock_quantity)
            if decrement_by > 0:
                target_model.objects.filter(pk=target_id).update(
                    stock_quantity=F("stock_quantity") - decrement_by
                )

        applied.append(
            StockChange(
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                sku=item.sku,
            )
        )

    logger.info(
        "Decremented stock for order %s: %d line(s)",
        order.number,
        len(applied),
    )
    return applied
