"""Read-side helpers. Totals are ALWAYS recomputed from current product prices."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.http import HttpRequest

from apps.cart.models import Cart, CartItem


@dataclass(frozen=True)
class CartLine:
    item: CartItem
    unit_price: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class CartSummary:
    cart: Cart
    lines: list[CartLine]
    subtotal: Decimal
    currency: str
    item_count: int


def get_cart_for_request(request: HttpRequest) -> Cart | None:
    qs = Cart.objects.prefetch_related("items__product", "items__variant")
    if request.user.is_authenticated:
        return qs.filter(user=request.user).first()
    if request.session.session_key:
        return qs.filter(session_key=request.session.session_key).first()
    return None


def cart_line_totals(items: Iterable[CartItem]) -> list[CartLine]:
    """
    For each item, derive the CURRENT unit price from the product or variant.
    Variant overrides product if present. Never stored.
    """
    lines: list[CartLine] = []
    for item in items:
        unit_price = item.variant.unit_price if item.variant_id else item.product.unit_price
        lines.append(
            CartLine(
                item=item,
                unit_price=unit_price,
                line_total=unit_price * item.quantity,
            )
        )
    return lines


def get_cart_summary(cart: Cart | None) -> CartSummary | None:
    if cart is None:
        return None
    items = list(cart.items.all())
    lines = cart_line_totals(items)
    subtotal = sum((line.line_total for line in lines), Decimal("0.00"))
    currency = items[0].product.currency if items else "PKR"
    return CartSummary(
        cart=cart,
        lines=lines,
        subtotal=subtotal,
        currency=currency,
        item_count=sum(item.quantity for item in items),
    )
