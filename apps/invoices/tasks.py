from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="invoices.generate_invoice")
def generate_invoice(order_id: int) -> str:
    """
    Fired when an order transitions to PAID. Creates the Invoice row (with
    a sequential immutable number) and queues PDF rendering.
    """
    from apps.invoices.services import create_invoice_for_order
    from apps.orders.models import Order

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("Order %s missing — skipping invoice", order_id)
        return ""

    invoice = create_invoice_for_order(order=order)
    render_invoice_pdf.delay(invoice.pk)
    return invoice.number


@shared_task(name="invoices.render_invoice_pdf")
def render_invoice_pdf(invoice_id: int) -> str:
    """Render and persist the PDF for an Invoice. Returns the file path or ""."""
    from apps.invoices.models import Invoice
    from apps.invoices.services import write_invoice_pdf

    invoice = Invoice.objects.filter(pk=invoice_id).first()
    if not invoice:
        logger.warning("Invoice %s missing — skipping PDF render", invoice_id)
        return ""
    write_invoice_pdf(invoice)
    return invoice.pdf.name
