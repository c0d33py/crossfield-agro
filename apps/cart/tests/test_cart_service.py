from __future__ import annotations

from django.core.exceptions import ValidationError

import pytest

from apps.cart.models import Cart
from apps.cart.selectors import get_cart_summary
from apps.cart.services import (
    add_item,
    clear_cart,
    merge_session_cart_into_user_cart,
    remove_item,
    update_quantity,
)
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db


def _cart(**kw) -> Cart:
    kw.setdefault("session_key", "test-session-abc")
    return Cart.objects.create(**kw)


class TestAddItem:
    def test_adds_first_item(self):
        cart = _cart()
        product = make_published_product()
        item = add_item(cart=cart, product=product, quantity=2)
        assert item.quantity == 2

    def test_dedup_increments_quantity(self):
        cart = _cart()
        product = make_published_product()
        add_item(cart=cart, product=product, quantity=2)
        add_item(cart=cart, product=product, quantity=3)
        assert cart.items.count() == 1
        assert cart.items.first().quantity == 5

    def test_rejects_unpublished_product(self):
        from apps.products.tests.factories import make_product

        cart = _cart()
        product = make_product()  # draft
        with pytest.raises(ValidationError):
            add_item(cart=cart, product=product, quantity=1)

    def test_rejects_over_stock(self):
        cart = _cart()
        product = make_published_product(stock_quantity=2)
        with pytest.raises(ValidationError):
            add_item(cart=cart, product=product, quantity=5)


class TestCartSummary:
    def test_subtotal_is_recomputed_from_current_price(self):
        from decimal import Decimal

        cart = _cart()
        product = make_published_product()
        add_item(cart=cart, product=product, quantity=2)

        # Simulate a price change AFTER the item was added.
        product.unit_price = Decimal("999.99")
        product.save(update_fields=["unit_price"])

        summary = get_cart_summary(cart)
        assert summary.subtotal == Decimal(
            "1999.98"
        ), "subtotal must reflect current price, not snapshot"


class TestUpdateQuantity:
    def test_zero_quantity_removes_item(self):
        cart = _cart()
        product = make_published_product()
        item = add_item(cart=cart, product=product, quantity=1)
        update_quantity(item=item, quantity=0)
        assert cart.items.count() == 0


class TestClearCart:
    def test_removes_all_items(self):
        from apps.products.tests.factories import make_category

        cart = _cart()
        cat = make_category()  # share category so two products don't collide on slug
        a = make_published_product(category=cat, sku="A", slug="a")
        b = make_published_product(category=cat, sku="B", slug="b")
        add_item(cart=cart, product=a, quantity=1)
        add_item(cart=cart, product=b, quantity=1)
        clear_cart(cart=cart)
        assert cart.items.count() == 0


class TestMergeOnLogin:
    def test_merges_session_cart_into_user(self, django_user_model):
        product = make_published_product()
        session_cart = Cart.objects.create(session_key="anon-key")
        add_item(cart=session_cart, product=product, quantity=2)

        user = django_user_model.objects.create_user(username="u", password="x")
        merged = merge_session_cart_into_user_cart(session_key="anon-key", user=user)

        assert merged.items.count() == 1
        assert merged.items.first().quantity == 2
        assert not Cart.objects.filter(pk=session_cart.pk).exists()


class TestRemoveItem:
    def test_bumps_cart_updated_at(self):
        """
        Regression: remove_item used to write item.cart.updated_at back to the
        row, but that's the stale pre-delete timestamp — cart expiry would
        kick in earlier than intended. The fix relies on auto_now=True.
        """
        import time

        cart = _cart()
        product = make_published_product()
        add_item(cart=cart, product=product, quantity=1)
        cart.refresh_from_db()
        before = cart.updated_at

        time.sleep(0.01)  # auto_now resolution is microseconds; one tick is enough
        item = cart.items.first()
        remove_item(item=item)

        cart.refresh_from_db()
        assert (
            cart.updated_at > before
        ), "remove_item must bump updated_at so cart-expiry stays accurate"
