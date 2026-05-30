from __future__ import annotations

from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.views.generic import View

from apps.invoices.models import Invoice


class InvoiceDownloadView(View):
    """
    PDF download. Logged-in users can fetch their own orders' invoices.
    Anonymous guests need both the invoice number AND the order UUID
    (passed as ?token=<uuid>) — mirrors the order tracking gate.
    """

    def get(self, request: HttpRequest, number: str) -> HttpResponse:
        invoice = Invoice.objects.filter(number=number).select_related("order").first()
        if invoice is None or not invoice.pdf:
            raise Http404("Invoice not found")

        order = invoice.order
        if request.user.is_authenticated and order.user_id == request.user.id:
            authorised = True
        else:
            token = request.GET.get("token", "")
            authorised = token == str(order.uuid)

        if not authorised:
            raise Http404("Invoice not found")

        return FileResponse(invoice.pdf.open("rb"), as_attachment=True, filename=f"{number}.pdf")
