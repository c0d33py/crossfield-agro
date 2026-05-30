from __future__ import annotations

from uuid import UUID

from django.db.models import QuerySet

from apps.orders.models import Order


def get_order_for_user(*, user, order_uuid: UUID) -> Order | None:
    return (
        Order.objects.filter(uuid=order_uuid, user=user).prefetch_related("items", "events").first()
    )


def get_order_by_uuid(order_uuid: UUID) -> Order | None:
    return Order.objects.filter(uuid=order_uuid).prefetch_related("items", "events").first()


def get_order_by_number(*, number: str) -> Order | None:
    """Public tracking lookup. Rate-limited at the view layer to defeat enumeration."""
    return Order.objects.filter(number=number).prefetch_related("events").first()


def get_user_orders(user) -> QuerySet[Order]:
    return Order.objects.filter(user=user).only(
        "id", "uuid", "number", "grand_total", "currency", "cached_status", "created_at"
    )
