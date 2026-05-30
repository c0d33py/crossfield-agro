"""Public order tracking — order-number-only lookup with rate limiting."""

from __future__ import annotations

from decimal import Decimal

from django.core.cache import cache
from django.urls import reverse

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.orders.models import OrderEventType
from apps.orders.services import create_order_from_cart, transition_order
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    # django-ratelimit uses the default cache for counters.
    cache.clear()
    yield
    cache.clear()


def _addr() -> dict:
    return {
        "name": "SENTINEL_NAME",
        "line1": "SENTINEL_STREET_LINE_99",
        "city": "Lahore",
        "postal_code": "54000",
        "country": "PK",
    }


def _make_order(email="buyer@example.com"):
    cart = Cart.objects.create(session_key=f"trk-{id(object())}")
    p = make_published_product(unit_price=Decimal("100.00"), stock_quantity=10)
    add_item(cart=cart, product=p, quantity=1)
    return create_order_from_cart(
        cart=cart,
        email=email,
        shipping_address=_addr(),
        billing_address=_addr(),
    )


class TestTrackForm:
    def test_renders_form(self, client):
        response = client.get(reverse("orders:track"))
        assert response.status_code == 200
        assert b"Track your order" in response.content
        # Email field must be gone.
        assert b'name="email"' not in response.content

    def test_redirects_to_detail_on_valid_lookup(self, client):
        order = _make_order()
        response = client.post(reverse("orders:track"), {"order_number": order.number})
        assert response.status_code == 302
        assert response.url == reverse("orders:track-detail", kwargs={"order_number": order.number})

    def test_order_number_is_normalised(self, client):
        order = _make_order()
        response = client.post(
            reverse("orders:track"),
            {
                "order_number": f"  {order.number.lower()}  ",
            },
        )
        assert response.status_code == 302

    def test_rejects_unknown_order(self, client):
        _make_order()
        response = client.post(
            reverse("orders:track"),
            {
                "order_number": "CA-99999999-FAKE00",
            },
        )
        assert response.status_code == 200
        assert b"couldn&#x27;t find" in response.content or b"couldn't find" in response.content


class TestTrackDetail:
    def test_renders_status(self, client):
        order = _make_order()
        url = reverse("orders:track-detail", kwargs={"order_number": order.number})
        response = client.get(url)
        assert response.status_code == 200
        assert order.number.encode() in response.content
        assert b"Pending" in response.content

    def test_404_for_unknown_order(self, client):
        response = client.get(
            reverse("orders:track-detail", kwargs={"order_number": "CA-99999999-NOPE00"})
        )
        assert response.status_code == 404

    def test_surfaces_tracking_number_when_shipped(self, client):
        order = _make_order()
        transition_order(order=order, to_state=OrderEventType.CONFIRMED)
        transition_order(order=order, to_state=OrderEventType.PAID)
        transition_order(order=order, to_state=OrderEventType.PROCESSING)
        transition_order(
            order=order,
            to_state=OrderEventType.SHIPPED,
            metadata={"tracking_number": "TCS123456789", "carrier": "TCS"},
        )
        url = reverse("orders:track-detail", kwargs={"order_number": order.number})
        response = client.get(url)
        assert response.status_code == 200
        assert b"TCS123456789" in response.content
        assert b"TCS" in response.content

    def test_does_not_expose_prices_or_address(self, client):
        # Order number is now the only credential — even more important that
        # we don't leak line totals or shipping address through this page.
        order = _make_order()
        url = reverse("orders:track-detail", kwargs={"order_number": order.number})
        response = client.get(url)
        assert str(order.grand_total).encode() not in response.content
        assert b"SENTINEL_STREET_LINE_99" not in response.content
        assert b"SENTINEL_NAME" not in response.content


class TestRateLimit:
    def test_track_form_blocks_after_10_posts(self, client):
        # First 10 POSTs are allowed (succeed or render the not-found form).
        for _ in range(10):
            response = client.post(
                reverse("orders:track"),
                {
                    "order_number": "CA-99999999-NOPE00",
                },
            )
            assert response.status_code == 200
        # 11th is blocked by django-ratelimit.
        response = client.post(
            reverse("orders:track"),
            {
                "order_number": "CA-99999999-NOPE00",
            },
        )
        assert response.status_code == 403
