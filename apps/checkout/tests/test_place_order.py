from __future__ import annotations

from decimal import Decimal

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.checkout.services import place_order
from apps.orders.models import OrderEventType
from apps.payments.models import Payment, PaymentStatus
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


def _addr() -> dict:
    return {"line1": "x", "city": "Lahore", "postal_code": "54000", "country": "PK"}


class TestPlaceOrder:
    def test_creates_order_and_intent_atomically(self):
        cart = Cart.objects.create(session_key="co")
        p = make_published_product(unit_price=Decimal("250.00"), stock_quantity=5)
        add_item(cart=cart, product=p, quantity=2)

        result = place_order(
            cart=cart,
            email="b@example.com",
            shipping_address=_addr(),
            billing_address=_addr(),
            gateway_name="bank_transfer",
        )

        assert result.order.grand_total == Decimal("500.00")
        # cached_status is updated via Order.objects.filter().update() inside
        # transition_order, so the in-memory result.order is stale until refresh.
        result.order.refresh_from_db()
        assert result.order.cached_status == OrderEventType.CONFIRMED
        payment = Payment.objects.get(order=result.order)
        assert payment.status == PaymentStatus.INITIATED
        assert payment.amount == Decimal("500.00")
        assert cart.items.count() == 0
