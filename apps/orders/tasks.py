from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="orders.send_order_confirmation")
def send_order_confirmation(order_id: int) -> None:
    from apps.orders.models import Order

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("Order %s missing — skipping confirmation email", order_id)
        return
    logger.info("TODO: send order confirmation email for %s to %s", order.number, order.email)


@shared_task(name="orders.send_shipped_notification")
def send_shipped_notification(order_id: int, tracking_number: str = "") -> None:
    from apps.orders.models import Order

    order = Order.objects.filter(pk=order_id).first()
    if not order:
        return
    logger.info("TODO: send shipped email for %s, tracking=%s", order.number, tracking_number)


@shared_task(name="orders.auto_cancel_unpaid")
def auto_cancel_unpaid(timeout_minutes: int = 30) -> int:
    """Beat task: cancel CONFIRMED orders with no payment after timeout."""
    from django.utils import timezone

    from apps.orders.models import Order, OrderEventType
    from apps.orders.services import transition_order

    cutoff = timezone.now() - timezone.timedelta(minutes=timeout_minutes)
    stuck = Order.objects.filter(cached_status=OrderEventType.CONFIRMED, created_at__lt=cutoff)
    count = 0
    for order in stuck:
        try:
            transition_order(
                order=order,
                to_state=OrderEventType.CANCELLED,
                metadata={"reason": "payment_timeout"},
            )
            count += 1
        except Exception as e:
            logger.exception("Failed to auto-cancel order %s: %s", order.number, e)
    return count
