from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.orders.models import OrderEvent, OrderEventType
from apps.orders.services import create_order_from_cart, transition_order
from apps.orders.validators import InvalidOrderTransition
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


def _addr() -> dict:
    return {
        "name": "Test Buyer",
        "line1": "1 Mall Road",
        "city": "Lahore",
        "postal_code": "54000",
        "country": "PK",
    }


class TestCreateOrderFromCart:
    def test_creates_order_with_snapshots(self):
        cart = Cart.objects.create(session_key="s1")
        p = make_published_product(unit_price=Decimal("100.00"), stock_quantity=10)
        add_item(cart=cart, product=p, quantity=2)

        order = create_order_from_cart(
            cart=cart,
            email="buyer@example.com",
            shipping_address=_addr(),
            billing_address=_addr(),
        )

        assert order.subtotal == Decimal("200.00")
        assert order.grand_total == Decimal("200.00")
        assert order.items.count() == 1
        item = order.items.first()
        assert item.product_name == p.name
        assert item.unit_price == Decimal("100.00")  # snapshot

    def test_snapshot_survives_price_change(self):
        cart = Cart.objects.create(session_key="s2")
        p = make_published_product(unit_price=Decimal("100.00"), stock_quantity=10)
        add_item(cart=cart, product=p, quantity=1)
        order = create_order_from_cart(
            cart=cart, email="x@x.com", shipping_address=_addr(), billing_address=_addr()
        )

        p.unit_price = Decimal("999.99")
        p.save(update_fields=["unit_price"])

        assert order.items.first().unit_price == Decimal("100.00"), "snapshot must not change"

    def test_creates_pending_event(self):
        cart = Cart.objects.create(session_key="s3")
        p = make_published_product()
        add_item(cart=cart, product=p, quantity=1)
        order = create_order_from_cart(
            cart=cart, email="x@x.com", shipping_address=_addr(), billing_address=_addr()
        )
        assert order.events.count() == 1
        assert order.events.first().event_type == OrderEventType.PENDING

    def test_empties_cart(self):
        cart = Cart.objects.create(session_key="s4")
        p = make_published_product()
        add_item(cart=cart, product=p, quantity=1)
        create_order_from_cart(
            cart=cart, email="x@x.com", shipping_address=_addr(), billing_address=_addr()
        )
        assert cart.items.count() == 0

    def test_rejects_insufficient_stock(self):
        cart = Cart.objects.create(session_key="s5")
        p = make_published_product(stock_quantity=10)
        add_item(cart=cart, product=p, quantity=3)
        # Stock drained between cart-add and checkout
        p.stock_quantity = 1
        p.save(update_fields=["stock_quantity"])

        with pytest.raises(ValidationError):
            create_order_from_cart(
                cart=cart, email="x@x.com", shipping_address=_addr(), billing_address=_addr()
            )


class TestTransitionOrder:
    def _make_order(self):
        cart = Cart.objects.create(session_key="tx")
        p = make_published_product()
        add_item(cart=cart, product=p, quantity=1)
        return create_order_from_cart(
            cart=cart, email="x@x.com", shipping_address=_addr(), billing_address=_addr()
        )

    def test_legal_transition(self):
        order = self._make_order()
        transition_order(order=order, to_state=OrderEventType.CONFIRMED)
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.CONFIRMED
        assert order.current_status == OrderEventType.CONFIRMED

    def test_rejects_illegal_transition(self):
        order = self._make_order()
        # PENDING -> SHIPPED is not allowed
        with pytest.raises(InvalidOrderTransition):
            transition_order(order=order, to_state=OrderEventType.SHIPPED)

    def test_appends_event_does_not_mutate(self):
        order = self._make_order()
        before = order.events.count()
        transition_order(order=order, to_state=OrderEventType.CANCELLED)
        assert order.events.count() == before + 1
        # The original PENDING event is still there
        assert OrderEvent.objects.filter(order=order, event_type=OrderEventType.PENDING).exists()
