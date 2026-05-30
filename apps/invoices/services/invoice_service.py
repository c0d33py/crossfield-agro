from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.invoices.models import Invoice, InvoiceSequence
from apps.orders.models import Order


def _pakistan_fiscal_year(now=None) -> int:
    """Pakistan FY runs Jul 1 - Jun 30. FY2025 = Jul 2024 - Jun 2025."""
    now = now or timezone.now()
    return now.year if now.month >= 7 else now.year - 1 + 1  # Jul–Dec belongs to FY ending next Jun


@transaction.atomic
def allocate_invoice_number(fiscal_year: int | None = None) -> tuple[int, str]:
    """
    Reserve the next number atomically. Returns (sequence, formatted_number).
    Numbers never repeat; sequence resets per fiscal year.
    """
    fy = fiscal_year or _pakistan_fiscal_year()
    seq, _ = InvoiceSequence.objects.select_for_update().get_or_create(fiscal_year=fy)
    seq.last_number += 1
    seq.save(update_fields=["last_number"])
    return fy, f"INV-{fy}-{seq.last_number:06d}"


@transaction.atomic
def create_invoice_for_order(*, order: Order) -> Invoice:
    """Idempotent: returns existing invoice if order already has one."""
    existing = Invoice.objects.filter(order=order).first()
    if existing is not None:
        return existing
    fy, number = allocate_invoice_number()
    return Invoice.objects.create(order=order, number=number, fiscal_year=fy)
