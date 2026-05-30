"""Tests for the order confirmation page + status endpoint."""

from __future__ import annotations

from decimal import Decimal

from django.urls import reverse

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.orders.models import OrderEventType
from apps.orders.services import create_order_from_cart, transition_order
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


def _addr() -> dict:
    return {
        "name": "X",
        "line1": "x",
        "city": "Lahore",
        "postal_code": "54000",
        "country": "PK",
    }


def _make_order():
    cart = Cart.objects.create(session_key=f"ord-{id(object())}")
    p = make_published_product(unit_price=Decimal("100.00"), stock_quantity=10)
    add_item(cart=cart, product=p, quantity=1)
    return create_order_from_cart(
        cart=cart,
        email="b@example.com",
        shipping_address=_addr(),
        billing_address=_addr(),
    )


class TestOrderConfirmation:
    def test_404_for_unknown_order(self, client):
        from uuid import uuid4

        response = client.get(reverse("orders:confirmation", kwargs={"order_uuid": uuid4()}))
        assert response.status_code == 404

    def test_redirects_to_return_page_when_not_paid(self, client):
        order = _make_order()  # status: PENDING
        response = client.get(reverse("orders:confirmation", kwargs={"order_uuid": order.uuid}))
        assert response.status_code == 302
        assert response.url == reverse("checkout:return", kwargs={"order_uuid": order.uuid})

    def test_renders_when_paid(self, client):
        order = _make_order()
        transition_order(order=order, to_state=OrderEventType.CONFIRMED)
        transition_order(order=order, to_state=OrderEventType.PAID)

        response = client.get(reverse("orders:confirmation", kwargs={"order_uuid": order.uuid}))
        assert response.status_code == 200
        assert order.number.encode() in response.content
        assert b"Thank you" in response.content
        assert b"View Order Details" in response.content

    def test_renders_when_processing(self, client):
        order = _make_order()
        transition_order(order=order, to_state=OrderEventType.CONFIRMED)
        transition_order(order=order, to_state=OrderEventType.PAID)
        transition_order(order=order, to_state=OrderEventType.PROCESSING)

        response = client.get(reverse("orders:confirmation", kwargs={"order_uuid": order.uuid}))
        assert response.status_code == 200
        assert b"confirmed" in response.content.lower()


class TestStatusEndpoint:
    def test_returns_json_status_for_anonymous(self, client):
        """Status endpoint must work for anonymous guest-checkout buyers."""
        order = _make_order()
        response = client.get(reverse("orders:status", kwargs={"order_uuid": order.uuid}))
        assert response.status_code == 200
        data = response.json()
        assert data["number"] == order.number
        assert data["status"] == "pending"

    def test_reflects_status_changes(self, client):
        order = _make_order()
        transition_order(order=order, to_state=OrderEventType.CONFIRMED)
        transition_order(order=order, to_state=OrderEventType.PAID)
        response = client.get(reverse("orders:status", kwargs={"order_uuid": order.uuid}))
        assert response.json()["status"] == "paid"
