from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.orders.models import Order, OrderEventType
from apps.orders.services import transition_order
from apps.shipping.models import ShippingMethod, ShippingRate


def quote_shipping(*, method: ShippingMethod, country: str, total_weight_kg: Decimal) -> Decimal:
    """Returns the rate price for the given method/country/weight band."""
    rate = (
        ShippingRate.objects.filter(
            method=method,
            country=country,
            min_weight_kg__lte=total_weight_kg,
            max_weight_kg__gte=total_weight_kg,
        )
        .order_by("min_weight_kg")
        .first()
    )
    if rate is None:
        raise ValueError(
            f"No shipping rate for method={method.code}, country={country}, weight={total_weight_kg}"
        )
    return rate.price


@transaction.atomic
def mark_shipped(
    *,
    order: Order,
    tracking_number: str,
    carrier: str = "",
    actor=None,
):
    """Append a SHIPPED event; queue the carrier notification email."""
    event = transition_order(
        order=order,
        to_state=OrderEventType.SHIPPED,
        actor=actor,
        metadata={"tracking_number": tracking_number, "carrier": carrier},
    )
    from apps.orders.tasks import send_shipped_notification

    send_shipped_notification.delay(order.pk, tracking_number)
    return event
