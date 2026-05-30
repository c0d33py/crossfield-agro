"""WeasyPrint-based PDF renderer for Invoice rows."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from apps.invoices.models import Invoice

logger = logging.getLogger(__name__)


def _logo_file_uri() -> str:
    """
    Resolve the brand logo to an absolute file:// URI for WeasyPrint.
    WeasyPrint renders headlessly so it can't use {% static %} URLs —
    it needs a real filesystem path.
    """
    path = finders.find("core/img/logo/crossfield-logo.png")
    if not path:
        return ""
    return Path(path).resolve().as_uri()


def render_invoice_to_pdf(invoice: Invoice) -> bytes:
    """Render the invoice HTML template to PDF bytes via WeasyPrint."""
    # Import inside the function so test collection doesn't pay the cost.
    from weasyprint import HTML

    order = invoice.order
    cod_payment = order.payments.filter(gateway="cod").exists()
    html = render_to_string(
        "invoices/invoice_pdf.html",
        {
            "invoice": invoice,
            "order": order,
            "cod_payment": cod_payment,
            "logo_uri": _logo_file_uri(),
        },
    )
    buf = BytesIO()
    HTML(string=html).write_pdf(target=buf)
    return buf.getvalue()


def write_invoice_pdf(invoice: Invoice) -> Invoice:
    """Render the PDF and attach it to the Invoice.pdf FileField. Idempotent
    in the sense that re-running overwrites with the current state — useful
    when a Proforma is re-rendered as a Tax Invoice after payment clears."""
    pdf_bytes = render_invoice_to_pdf(invoice)
    filename = f"{invoice.number}.pdf"
    invoice.pdf.save(filename, ContentFile(pdf_bytes), save=True)
    logger.info("Rendered PDF for invoice %s (%d bytes)", invoice.number, len(pdf_bytes))
    return invoice
