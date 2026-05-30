from __future__ import annotations

from apps.payments.models import Payment


def get_latest_payment_for_order(order_id: int) -> Payment | None:
    return Payment.objects.filter(order_id=order_id).order_by("-created_at").first()


def get_payment_by_intent_id(intent_id: str) -> Payment | None:
    return Payment.objects.filter(gateway_intent_id=intent_id).first()
