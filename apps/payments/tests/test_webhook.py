"""Tests the webhook idempotency + signature flow with a fake gateway."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.orders.models import OrderEventType
from apps.orders.services import create_order_from_cart
from apps.payments.gateways.base import (
    GatewayAdapter,
    GatewayEvent,
    GatewayStatus,
    IntentResponse,
    WebhookSignatureError,
    register_gateway,
)
from apps.payments.models import Payment, PaymentEvent, PaymentStatus
from apps.payments.services import create_payment_intent, handle_webhook
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


class _FakeGateway(GatewayAdapter):
    name = "fake"
    EXPECTED_SIG = "good-sig"

    def create_intent(self, *, amount, currency, reference, return_url, webhook_url):
        return IntentResponse(
            gateway=self.name, intent_id=f"int_{reference}", redirect_url=return_url
        )

    def verify_signature(self, payload, signature):
        if signature != self.EXPECTED_SIG:
            raise WebhookSignatureError("bad sig")

    def parse(self, payload):
        d = json.loads(payload.decode())
        return GatewayEvent(event_id=d["event_id"], type=d["type"], intent_id=d["intent_id"])

    def fetch_status(self, intent_id):
        return GatewayStatus(intent_id=intent_id, is_terminal=False, succeeded=False)


@pytest.fixture(autouse=True)
def _register_fake():
    register_gateway("fake", _FakeGateway())


def _make_order():
    cart = Cart.objects.create(session_key="pay")
    p = make_published_product(unit_price=Decimal("500.00"), stock_quantity=10)
    add_item(cart=cart, product=p, quantity=1)
    return create_order_from_cart(
        cart=cart,
        email="x@x.com",
        shipping_address={"line1": "x"},
        billing_address={"line1": "x"},
    )


class TestCreatePaymentIntent:
    def test_creates_payment_and_confirms_order(self):
        order = _make_order()
        resp = create_payment_intent(order=order, gateway_name="fake")
        assert resp.intent_id.startswith("int_")
        payment = Payment.objects.get(gateway_intent_id=resp.intent_id)
        assert payment.amount == Decimal("500.00")
        assert payment.status == PaymentStatus.INITIATED
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.CONFIRMED


class TestHandleWebhook:
    def _payload(self, intent_id, event_id="evt_1", type_="payment.succeeded"):
        return json.dumps({"event_id": event_id, "type": type_, "intent_id": intent_id}).encode()

    def test_marks_order_paid_on_success(self):
        order = _make_order()
        resp = create_payment_intent(order=order, gateway_name="fake")
        handle_webhook(
            gateway_name="fake",
            payload=self._payload(resp.intent_id),
            signature=_FakeGateway.EXPECTED_SIG,
        )
        payment = Payment.objects.get(gateway_intent_id=resp.intent_id)
        assert payment.status == PaymentStatus.SUCCEEDED
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.PAID

    def test_rejects_bad_signature(self):
        order = _make_order()
        resp = create_payment_intent(order=order, gateway_name="fake")
        with pytest.raises(WebhookSignatureError):
            handle_webhook(
                gateway_name="fake",
                payload=self._payload(resp.intent_id),
                signature="WRONG",
            )

    def test_idempotent_on_duplicate_event(self):
        order = _make_order()
        resp = create_payment_intent(order=order, gateway_name="fake")

        handle_webhook(
            gateway_name="fake",
            payload=self._payload(resp.intent_id, event_id="evt_42"),
            signature=_FakeGateway.EXPECTED_SIG,
        )
        # Same event_id again
        handle_webhook(
            gateway_name="fake",
            payload=self._payload(resp.intent_id, event_id="evt_42"),
            signature=_FakeGateway.EXPECTED_SIG,
        )

        assert PaymentEvent.objects.filter(gateway_event_id="evt_42").count() == 1
        # And the order is still in PAID, not somehow double-transitioned
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.PAID

    def test_failure_event_marks_payment_failed(self):
        order = _make_order()
        resp = create_payment_intent(order=order, gateway_name="fake")
        handle_webhook(
            gateway_name="fake",
            payload=self._payload(resp.intent_id, event_id="evt_fail", type_="payment.failed"),
            signature=_FakeGateway.EXPECTED_SIG,
        )
        payment = Payment.objects.get(gateway_intent_id=resp.intent_id)
        assert payment.status == PaymentStatus.FAILED
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.PAYMENT_FAILED
