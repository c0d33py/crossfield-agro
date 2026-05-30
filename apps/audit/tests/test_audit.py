from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model

import pytest

from apps.audit.models import AuditAction, AuditLogEntry
from apps.audit.services import log_action
from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.orders.models import OrderEventType
from apps.orders.services import create_order_from_cart, transition_order
from apps.products.tests.factories import make_published_product

pytestmark = pytest.mark.django_db

User = get_user_model()


class TestLogActionService:
    def test_persists_with_target_snapshot(self):
        product = make_published_product(name="Urea 50kg", slug="urea-50kg", sku="U50")
        entry = log_action(
            action=AuditAction.PUBLISH,
            target=product,
            description="Published from admin.",
        )
        assert AuditLogEntry.objects.filter(pk=entry.pk).exists()
        assert entry.target_type == "products.Product"
        assert str(product.pk) == entry.target_id
        assert "Urea 50kg" in entry.target_label

    def test_actor_label_snapshot(self):
        user = User.objects.create_user(username="alice", email="alice@x.com", password="x")
        entry = log_action(action=AuditAction.OTHER, actor=user, description="x")
        assert entry.actor_label == "alice@x.com"

    def test_no_target_handled_cleanly(self):
        entry = log_action(action=AuditAction.OTHER, description="system event")
        assert entry.target_type == ""
        assert entry.target_id == ""


class TestOrderTransitionAutologs:
    def _make_order(self):
        cart = Cart.objects.create(session_key=f"a-{id(object())}")
        p = make_published_product(unit_price=Decimal("100.00"), stock_quantity=10)
        add_item(cart=cart, product=p, quantity=1)
        return create_order_from_cart(
            cart=cart,
            email="b@example.com",
            shipping_address={
                "name": "X",
                "line1": "x",
                "city": "L",
                "postal_code": "54000",
                "country": "PK",
            },
            billing_address={
                "name": "X",
                "line1": "x",
                "city": "L",
                "postal_code": "54000",
                "country": "PK",
            },
        )

    def test_transition_creates_audit_entry(self):
        order = self._make_order()
        before = AuditLogEntry.objects.filter(action=AuditAction.ORDER_TRANSITION).count()
        transition_order(order=order, to_state=OrderEventType.CONFIRMED)
        after = AuditLogEntry.objects.filter(action=AuditAction.ORDER_TRANSITION).count()
        assert after == before + 1

        entry = AuditLogEntry.objects.filter(
            action=AuditAction.ORDER_TRANSITION, target_type="orders.Order"
        ).first()
        assert entry is not None
        assert entry.metadata.get("to") == OrderEventType.CONFIRMED


class TestLoginSignal:
    def test_failed_login_logged(self, client):
        # Trigger Django's user_login_failed signal via admin login attempt
        client.post(
            "/admin/login/",
            data={
                "username": "nosuchuser",
                "password": "wrong",
            },
        )
        assert AuditLogEntry.objects.filter(action=AuditAction.LOGIN_FAILED).exists()
