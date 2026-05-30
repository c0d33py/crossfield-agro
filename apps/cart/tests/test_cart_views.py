"""Tests for cart views, drawer fragment, and context processor."""

from __future__ import annotations

from decimal import Decimal

from django.urls import reverse

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


def _seed_cart(client):
    product = make_published_product(unit_price=Decimal("100.00"), stock_quantity=20)
    client.get(reverse("products:product-list"))
    cart, _ = Cart.objects.get_or_create(session_key=client.session.session_key)
    add_item(cart=cart, product=product, quantity=3)
    return product, cart


class TestCartFragment:
    def test_returns_empty_state_when_no_cart(self, client):
        response = client.get(reverse("cart:fragment"))
        assert response.status_code == 200
        assert b"Empty" in response.content
        assert b"Browse Products" in response.content

    def test_returns_lines_when_cart_has_items(self, client):
        product, _ = _seed_cart(client)
        response = client.get(reverse("cart:fragment"))
        assert response.status_code == 200
        assert product.name.encode() in response.content
        assert b"3 items" in response.content or b"3 item" in response.content
        # Drawer subtotal
        assert b"300.00" in response.content


class TestCartContextProcessor:
    def test_summary_injected_into_every_page(self, client):
        _seed_cart(client)
        # Hit a non-cart page and verify the badge shows up in the header
        response = client.get(reverse("core:home"))
        assert response.status_code == 200
        assert b"cart-trigger" in response.content
        assert b"cart-trigger__count" in response.content

    def test_no_badge_when_cart_empty(self, client):
        response = client.get(reverse("core:home"))
        assert response.status_code == 200
        # Trigger always present; the badge span (with data-cart-count attribute)
        # is absent when count == 0. The classname string still appears in inline JS.
        assert b"cart-trigger" in response.content
        assert b"data-cart-count>" not in response.content


class TestCartDetailRedesign:
    def test_empty_state_renders(self, client):
        response = client.get(reverse("cart:detail"))
        assert response.status_code == 200
        assert b"Your cart is empty" in response.content
        assert b"Browse Products" in response.content

    def test_populated_renders_with_summary(self, client):
        product, _ = _seed_cart(client)
        response = client.get(reverse("cart:detail"))
        assert response.status_code == 200
        assert product.name.encode() in response.content
        assert b"Proceed to Checkout" in response.content
        assert b"Order summary" in response.content
