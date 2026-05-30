"""End-to-end tests for the 3-step checkout flow."""

from __future__ import annotations

from decimal import Decimal

from django.urls import reverse

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.orders.models import Order
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


def _seed_cart(client) -> None:
    """Put a product in the session cart for `client`."""
    product = make_published_product(unit_price=Decimal("500.00"), stock_quantity=10)
    # Drive a real request so the session cart is created tied to client's session_key.
    client.get(reverse("products:product-list"))
    session_key = client.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key)
    add_item(cart=cart, product=product, quantity=2)
    return product


ADDRESS_DATA = {
    "email": "buyer@example.com",
    "shipping_name": "Test Buyer",
    "shipping_line1": "1 Mall Road",
    "shipping_line2": "",
    "shipping_city": "Lahore",
    "shipping_postal_code": "54000",
    "shipping_country": "PK",
    "shipping_phone": "+92 321 1234567",
    "billing_same_as_shipping": "on",
    "billing_name": "",
    "billing_line1": "",
    "billing_line2": "",
    "billing_city": "",
    "billing_postal_code": "",
    "billing_country": "",
}


class TestCheckoutStart:
    def test_get_redirects_to_address_step(self, client):
        response = client.get(reverse("checkout:start"))
        assert response.status_code == 302
        assert response.url == reverse("checkout:address")


class TestAddressStep:
    def test_empty_cart_redirects_back_to_cart(self, client):
        response = client.get(reverse("checkout:address"))
        assert response.status_code == 302
        assert response.url == reverse("cart:detail")

    def test_renders_form(self, client):
        _seed_cart(client)
        response = client.get(reverse("checkout:address"))
        assert response.status_code == 200
        assert b"Shipping" in response.content
        # Step indicator should show step 1 as current
        assert b'aria-current="step"' in response.content
        assert b"<h1>Shipping" in response.content or b"Shipping &amp; billing" in response.content

    def test_valid_post_persists_to_session_and_redirects(self, client):
        _seed_cart(client)
        response = client.post(reverse("checkout:address"), data=ADDRESS_DATA)
        assert response.status_code == 302
        assert response.url == reverse("checkout:review")
        # Session should hold the address payload
        state = client.session["checkout"]
        assert state["email"] == "buyer@example.com"
        assert state["shipping"]["city"] == "Lahore"
        assert state["billing_same"] is True
        # billing mirrors shipping
        assert state["billing"]["city"] == "Lahore"

    def test_invalid_phone_rejected(self, client):
        _seed_cart(client)
        bad = dict(ADDRESS_DATA, shipping_phone="not-a-number")
        response = client.post(reverse("checkout:address"), data=bad)
        assert response.status_code == 200
        assert b"valid Pakistani mobile" in response.content

    def test_separate_billing_requires_fields(self, client):
        _seed_cart(client)
        data = dict(ADDRESS_DATA)
        data.pop("billing_same_as_shipping")  # unchecked
        response = client.post(reverse("checkout:address"), data=data)
        assert response.status_code == 200
        # Some billing_* fields should now be marked required
        assert b"Required when billing differs" in response.content


class TestReviewStep:
    def test_without_address_redirects(self, client):
        _seed_cart(client)
        response = client.get(reverse("checkout:review"))
        assert response.status_code == 302
        assert response.url == reverse("checkout:address")

    def test_renders_address_summary(self, client):
        _seed_cart(client)
        client.post(reverse("checkout:address"), data=ADDRESS_DATA)
        response = client.get(reverse("checkout:review"))
        assert response.status_code == 200
        assert b"buyer@example.com" in response.content
        assert b"1 Mall Road" in response.content
        assert b"Same as shipping" in response.content
        # Step indicator: step 2 current, step 1 done
        assert b'aria-current="step"' in response.content


class TestPaymentStep:
    def test_without_address_redirects(self, client):
        _seed_cart(client)
        response = client.get(reverse("checkout:payment"))
        assert response.status_code == 302

    def test_renders_gateway_options(self, client):
        _seed_cart(client)
        client.post(reverse("checkout:address"), data=ADDRESS_DATA)
        response = client.get(reverse("checkout:payment"))
        assert response.status_code == 200
        assert b"Bank Transfer" in response.content
        assert b"terms-conditions" in response.content

    def test_valid_post_creates_order_and_clears_session_state(self, client):
        _seed_cart(client)
        client.post(reverse("checkout:address"), data=ADDRESS_DATA)
        before = Order.objects.count()
        response = client.post(
            reverse("checkout:payment"),
            data={
                "gateway": "bank_transfer",
                "accept_terms": "on",
            },
        )
        assert response.status_code == 302
        assert Order.objects.count() == before + 1
        # Session state for checkout should be cleared after order placed
        assert "checkout" not in client.session

    def test_requires_terms_acceptance(self, client):
        _seed_cart(client)
        client.post(reverse("checkout:address"), data=ADDRESS_DATA)
        response = client.post(reverse("checkout:payment"), data={"gateway": "bank_transfer"})
        # accept_terms missing -> form invalid -> 200 re-render
        assert response.status_code == 200
