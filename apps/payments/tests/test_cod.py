"""COD lifecycle: PENDING on creation, staff call-back confirms + decrements stock."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.orders.models import OrderEventType
from apps.orders.services import create_order_from_cart
from apps.payments.models import Payment, PaymentStatus
from apps.payments.services import (
    confirm_cod_order,
    create_payment_intent,
    mark_cod_received,
)
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


def _order(stock=5, qty=2):
    cart = Cart.objects.create(session_key=f"cod-{stock}-{qty}")
    p = make_published_product(unit_price=Decimal("100.00"), stock_quantity=stock)
    add_item(cart=cart, product=p, quantity=qty)
    return (
        create_order_from_cart(
            cart=cart,
            email="b@example.com",
            shipping_address={"line1": "x"},
            billing_address={"line1": "x"},
        ),
        p,
    )


class TestCreateCODIntent:
    def test_auto_confirms_order(self):
        order, _ = _order()
        create_payment_intent(order=order, gateway_name="cod")
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.CONFIRMED

    def test_decrements_stock_at_checkout(self):
        order, product = _order(stock=5, qty=2)
        create_payment_intent(order=order, gateway_name="cod")
        product.refresh_from_db()
        assert product.stock_quantity == 3

    def test_payment_starts_initiated(self):
        order, _ = _order()
        create_payment_intent(order=order, gateway_name="cod")
        payment = Payment.objects.get(order=order, gateway="cod")
        assert payment.status == PaymentStatus.INITIATED

    def test_blocks_when_stock_insufficient(self):
        """COD must refuse the order outright if stock isn't there at checkout."""
        from apps.cart.models import Cart
        from apps.cart.services import add_item
        from apps.orders.services import create_order_from_cart
        from apps.products.models import Product

        cart = Cart.objects.create(session_key="cod-short")
        # allow_backorder while building the order, then tighten it to force
        # the InsufficientStock branch when create_payment_intent runs.
        p = make_published_product(
            unit_price=Decimal("10"), stock_quantity=10, allow_backorder=True
        )
        add_item(cart=cart, product=p, quantity=3)
        order = create_order_from_cart(
            cart=cart,
            email="b@example.com",
            shipping_address={"line1": "x"},
            billing_address={"line1": "x"},
        )
        Product.objects.filter(pk=p.pk).update(stock_quantity=1, allow_backorder=False)
        with pytest.raises(ValidationError):
            create_payment_intent(order=order, gateway_name="cod")


class TestConfirmCODOrderRecovery:
    """confirm_cod_order is now a recovery action for stuck PENDING orders.
    Normal COD flow auto-confirms via create_payment_intent."""

    def test_noop_on_already_confirmed_order(self):
        """The common case under the new flow: order is already CONFIRMED
        by the time anyone clicks the admin action."""
        order, product = _order(stock=5, qty=2)
        create_payment_intent(order=order, gateway_name="cod")  # confirms + decrements
        confirm_cod_order(order=order)  # recovery click: must no-op
        product.refresh_from_db()
        assert product.stock_quantity == 3  # not double-decremented
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.CONFIRMED

    def test_recovers_a_pending_order(self):
        """Edge case: an order is sitting at PENDING (data fix, partial
        failure). The admin action moves it forward."""
        from apps.cart.models import Cart
        from apps.cart.services import add_item
        from apps.orders.services import create_order_from_cart

        cart = Cart.objects.create(session_key="stuck-pending")
        p = make_published_product(unit_price=Decimal("100"), stock_quantity=5)
        add_item(cart=cart, product=p, quantity=2)
        order = create_order_from_cart(
            cart=cart,
            email="b@example.com",
            shipping_address={"line1": "x"},
            billing_address={"line1": "x"},
        )
        # Hand-craft the stuck state: a COD Payment row but no CONFIRMED event.
        Payment.objects.create(
            order=order,
            gateway="cod",
            gateway_intent_id="cod_stuck_1",
            amount=order.grand_total,
            currency=order.currency,
            status=PaymentStatus.INITIATED,
        )
        assert order.current_status == OrderEventType.PENDING

        confirm_cod_order(order=order)

        order.refresh_from_db()
        assert order.cached_status == OrderEventType.CONFIRMED
        p.refresh_from_db()
        assert p.stock_quantity == 3


class TestMarkCODReceived:
    def test_flips_payment_to_succeeded(self):
        order, _ = _order()
        create_payment_intent(order=order, gateway_name="cod")  # auto-confirms
        mark_cod_received(order=order)
        payment = Payment.objects.get(order=order, gateway="cod")
        assert payment.status == PaymentStatus.SUCCEEDED

    def test_idempotent(self):
        order, _ = _order()
        create_payment_intent(order=order, gateway_name="cod")
        mark_cod_received(order=order)
        mark_cod_received(order=order)
        payment = Payment.objects.get(order=order, gateway="cod")
        assert payment.status == PaymentStatus.SUCCEEDED

    def test_does_not_transition_order(self):
        order, _ = _order()
        create_payment_intent(order=order, gateway_name="cod")
        order.refresh_from_db()
        before = order.cached_status
        mark_cod_received(order=order)
        order.refresh_from_db()
        assert order.cached_status == before

    def test_raises_when_no_cod_payment(self):
        order, _ = _order()
        with pytest.raises(ValidationError):
            mark_cod_received(order=order)


class TestConfirmCODOrderRaceSafety:
    def test_recovery_action_no_ops_on_already_confirmed_order(self):
        """
        confirm_cod_order is now a recovery action — under the normal flow
        the order is already CONFIRMED by create_payment_intent. The lock +
        re-read pattern still matters for the rare stuck-PENDING case, so we
        also keep an idempotency check here for the common (confirmed) path.
        """
        order, product = _order(stock=10, qty=3)
        create_payment_intent(order=order, gateway_name="cod")
        product.refresh_from_db()
        assert product.stock_quantity == 7  # auto-decremented at checkout

        # Stale reference — caller still thinks it's PENDING.
        stale = type(order).objects.get(pk=order.pk)
        assert stale.current_status == OrderEventType.CONFIRMED

        # Recovery action against an already-confirmed order must no-op
        # under the lock: no extra transition, no stock decrement.
        confirm_cod_order(order=stale)
        product.refresh_from_db()
        assert product.stock_quantity == 7, "stock must not double-decrement"
