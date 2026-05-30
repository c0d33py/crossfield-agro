from __future__ import annotations

import secrets
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.cart.models import Cart
from apps.cart.selectors import get_cart_summary
from apps.cart.services import clear_cart
from apps.orders.models import Order, OrderEvent, OrderEventType, OrderItem
from apps.orders.validators import validate_transition
from apps.products.validators import (
    validate_order_quantity_bounds,
    validate_stock_quantity,
)


def generate_order_number() -> str:
    return f"CA-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


@transaction.atomic
def create_order_from_cart(
    *,
    cart: Cart,
    email: str,
    shipping_address: dict,
    billing_address: dict,
    shipping_total: Decimal = Decimal("0.00"),
    tax_total: Decimal = Decimal("0.00"),
    discount_total: Decimal = Decimal("0.00"),
    user=None,
) -> Order:
    """
    Server-authoritative: revalidates every item against current product state,
    recomputes all totals, snapshots product data onto OrderItem, then empties cart.
    """
    summary = get_cart_summary(cart)
    if summary is None or not summary.lines:
        from django.core.exceptions import ValidationError

        raise ValidationError("Cart is empty.")

    subtotal = Decimal("0.00")
    snapshots: list[dict] = []
    for line in summary.lines:
        product = line.item.product
        variant = line.item.variant
        qty = line.item.quantity

        # Re-validate against current product state
        validate_stock_quantity(qty)
        validate_order_quantity_bounds(
            min_qty=product.min_order_quantity, max_qty=product.max_order_quantity
        )
        # Stock check using current quantity, not the cart-add-time value
        if product.track_inventory and not product.allow_backorder:
            available = variant.stock_quantity if variant else product.stock_quantity
            if qty > available:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    f"Insufficient stock for {product.name}: requested {qty}, available {available}"
                )

        unit_price = variant.unit_price if variant else product.unit_price
        line_total = unit_price * qty
        subtotal += line_total
        snapshots.append(
            {
                "product": product,
                "variant": variant,
                "product_name": product.name,
                "sku": variant.sku if variant else product.sku,
                "unit_price": unit_price,
                "quantity": qty,
                "line_total": line_total,
            }
        )

    grand_total = subtotal + shipping_total + tax_total - discount_total

    order = Order.objects.create(
        number=generate_order_number(),
        user=user,
        email=email,
        shipping_address=shipping_address,
        billing_address=billing_address,
        currency=summary.currency,
        subtotal=subtotal,
        shipping_total=shipping_total,
        tax_total=tax_total,
        discount_total=discount_total,
        grand_total=grand_total,
        cached_status=OrderEventType.PENDING,
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                product=s["product"],
                variant=s["variant"],
                product_name=s["product_name"],
                sku=s["sku"],
                unit_price=s["unit_price"],
                quantity=s["quantity"],
                line_total=s["line_total"],
            )
            for s in snapshots
        ]
    )
    OrderEvent.objects.create(order=order, event_type=OrderEventType.PENDING)
    clear_cart(cart=cart)
    return order


@transaction.atomic
def transition_order(
    *,
    order: Order,
    to_state: str,
    actor=None,
    metadata: dict | None = None,
) -> OrderEvent:
    """The ONLY way to change an order's status. Validates transition table."""
    current = order.current_status
    validate_transition(current=current, to_state=to_state)

    event = OrderEvent.objects.create(
        order=order,
        event_type=to_state,
        actor=actor,
        metadata=metadata or {},
    )
    # Maintain the read-side cache
    Order.objects.filter(pk=order.pk).update(cached_status=to_state)

    # Audit log — best-effort; never let logging failure abort the transition.
    try:
        from apps.audit.models import AuditAction
        from apps.audit.services import log_action

        log_action(
            action=AuditAction.ORDER_TRANSITION,
            actor=actor,
            target=order,
            description=f"Order {order.number}: {current} -> {to_state}",
            metadata={"from": current, "to": to_state, **(metadata or {})},
        )
    except Exception:
        pass

    # Issue an invoice on confirmation — every confirmed order gets one,
    # regardless of gateway. For prepaid orders the invoice is paid by the
    # time the customer sees it; for COD it's a proforma until the courier
    # returns cash. The Invoice row itself is gateway-agnostic; "paid" is
    # derived from order.payments status at display time.
    if to_state == OrderEventType.CONFIRMED:
        from apps.invoices.tasks import generate_invoice

        # transaction.on_commit so the Celery task isn't dispatched until the
        # OrderEvent row is actually visible to the worker.
        transaction.on_commit(lambda: generate_invoice.delay(order.id))

    return event
