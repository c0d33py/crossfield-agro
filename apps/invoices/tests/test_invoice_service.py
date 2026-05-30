from __future__ import annotations

from decimal import Decimal

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.invoices.models import Invoice
from apps.invoices.services import allocate_invoice_number, create_invoice_for_order
from apps.orders.services import create_order_from_cart
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


def _order():
    cart = Cart.objects.create(session_key=f"inv-{id(object())}")
    p = make_published_product(unit_price=Decimal("100"), stock_quantity=10)
    add_item(cart=cart, product=p, quantity=1)
    return create_order_from_cart(
        cart=cart,
        email="x@x.com",
        shipping_address={"line1": "x"},
        billing_address={"line1": "x"},
    )


class TestAllocateInvoiceNumber:
    def test_sequence_starts_at_one(self):
        fy, num = allocate_invoice_number(fiscal_year=2025)
        assert fy == 2025
        assert num.endswith("-000001")

    def test_sequence_increments(self):
        _, n1 = allocate_invoice_number(fiscal_year=2025)
        _, n2 = allocate_invoice_number(fiscal_year=2025)
        # extract trailing 6-digit numeric
        a = int(n1.split("-")[-1])
        b = int(n2.split("-")[-1])
        assert b == a + 1

    def test_separate_fiscal_years_have_separate_sequences(self):
        _, a = allocate_invoice_number(fiscal_year=2024)
        _, b = allocate_invoice_number(fiscal_year=2025)
        assert a.split("-")[-1] == b.split("-")[-1]  # both start at 000001
        assert "2024" in a
        assert "2025" in b


class TestCreateInvoiceForOrder:
    def test_creates_one_invoice(self):
        order = _order()
        invoice = create_invoice_for_order(order=order)
        assert invoice.order_id == order.id
        assert Invoice.objects.filter(order=order).count() == 1

    def test_idempotent(self):
        order = _order()
        a = create_invoice_for_order(order=order)
        b = create_invoice_for_order(order=order)
        assert a.pk == b.pk
        assert Invoice.objects.filter(order=order).count() == 1


# The on_commit-fired invoice generation needs a real commit, which pytest's
# default django_db wrapper suppresses. The next two classes use
# transaction=True so on_commit callbacks actually fire.
@pytest.mark.django_db(transaction=True)
class TestInvoiceOnEveryConfirmedOrder:
    """Regression: every confirmed order — including COD — must get an invoice."""

    def test_prepaid_order_gets_invoice_at_confirmation(self):
        """Prepaid gateway: order goes straight to CONFIRMED, invoice should fire."""
        from apps.payments.services import create_payment_intent

        order = _order()
        create_payment_intent(order=order, gateway_name="bank_transfer")
        assert Invoice.objects.filter(
            order=order
        ).exists(), "prepaid order must have invoice issued at CONFIRMED"

    def test_cod_order_gets_invoice_at_checkout(self):
        """COD now auto-confirms at intent creation, so the invoice fires immediately."""
        from apps.payments.services import create_payment_intent

        order = _order()
        create_payment_intent(order=order, gateway_name="cod")
        assert Invoice.objects.filter(
            order=order
        ).exists(), "COD order must have invoice issued at checkout"


@pytest.mark.django_db(transaction=True)
class TestInvoiceDocumentType:
    def test_unpaid_invoice_is_proforma(self):
        from apps.payments.services import create_payment_intent

        order = _order()
        create_payment_intent(order=order, gateway_name="bank_transfer")
        invoice = Invoice.objects.get(order=order)
        assert invoice.is_paid is False
        assert invoice.document_type == "Proforma Invoice"

    def test_paid_invoice_is_tax_invoice(self):
        """Once the gateway webhook flips the payment to SUCCEEDED, the
        same invoice row reads as a Tax Invoice."""
        from apps.orders.models import OrderEventType
        from apps.orders.services import transition_order
        from apps.payments.models import PaymentStatus
        from apps.payments.services import create_payment_intent

        order = _order()
        intent = create_payment_intent(order=order, gateway_name="bank_transfer")

        # Simulate webhook success directly (the full handle_webhook path
        # is covered in test_webhook.py).
        from apps.payments.models import Payment

        payment = Payment.objects.get(gateway_intent_id=intent.intent_id)
        payment.status = PaymentStatus.SUCCEEDED
        payment.save(update_fields=["status"])
        transition_order(order=order, to_state=OrderEventType.PAID)

        invoice = Invoice.objects.get(order=order)
        assert invoice.is_paid is True
        assert invoice.document_type == "Tax Invoice"


@pytest.mark.django_db(transaction=True)
class TestRenderInvoicePDF:
    def test_renders_pdf_and_attaches_to_invoice(self):
        from apps.invoices.services import write_invoice_pdf
        from apps.payments.services import create_payment_intent

        order = _order()
        create_payment_intent(order=order, gateway_name="bank_transfer")
        invoice = Invoice.objects.get(order=order)
        write_invoice_pdf(invoice)
        invoice.refresh_from_db()
        assert invoice.pdf, "PDF file must be attached"
        assert invoice.pdf.size > 0
        # First four bytes of any PDF are %PDF
        with invoice.pdf.open("rb") as f:
            assert f.read(4) == b"%PDF"


@pytest.mark.django_db(transaction=True)
class TestInvoiceDownloadGuestAccess:
    def test_guest_can_download_with_uuid_token(self, client):
        from apps.invoices.services import write_invoice_pdf
        from apps.payments.services import create_payment_intent

        order = _order()
        create_payment_intent(order=order, gateway_name="bank_transfer")
        invoice = Invoice.objects.get(order=order)
        write_invoice_pdf(invoice)

        url = f"/invoices/{invoice.number}/?token={order.uuid}"
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_guest_without_token_is_404(self, client):
        from apps.invoices.services import write_invoice_pdf
        from apps.payments.services import create_payment_intent

        order = _order()
        create_payment_intent(order=order, gateway_name="bank_transfer")
        invoice = Invoice.objects.get(order=order)
        write_invoice_pdf(invoice)

        response = client.get(f"/invoices/{invoice.number}/")
        assert response.status_code == 404

    def test_guest_with_wrong_token_is_404(self, client):
        from uuid import uuid4

        from apps.invoices.services import write_invoice_pdf
        from apps.payments.services import create_payment_intent

        order = _order()
        create_payment_intent(order=order, gateway_name="bank_transfer")
        invoice = Invoice.objects.get(order=order)
        write_invoice_pdf(invoice)

        response = client.get(f"/invoices/{invoice.number}/?token={uuid4()}")
        assert response.status_code == 404
