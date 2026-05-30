from __future__ import annotations

from apps.invoices.models import Invoice


def get_invoice_for_order(order_id: int) -> Invoice | None:
    return Invoice.objects.filter(order_id=order_id).first()


def get_invoice_by_number(number: str) -> Invoice | None:
    return Invoice.objects.filter(number=number).first()
