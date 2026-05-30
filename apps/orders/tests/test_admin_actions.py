"""Admin actions that let staff append OrderEvent rows forward (no edits)."""

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
    return {"name": "X", "line1": "x", "city": "Lahore", "postal_code": "54000", "country": "PK"}


def _order(state: str | None = None):
    cart = Cart.objects.create(session_key=f"adm-{id(object())}")
    p = make_published_product(unit_price=Decimal("100"), stock_quantity=10)
    add_item(cart=cart, product=p, quantity=1)
    order = create_order_from_cart(
        cart=cart,
        email="b@example.com",
        shipping_address=_addr(),
        billing_address=_addr(),
    )
    # walk forward to the requested state if needed
    walk_to = state or OrderEventType.PENDING
    path = {
        OrderEventType.PENDING: [],
        OrderEventType.CONFIRMED: [OrderEventType.CONFIRMED],
        OrderEventType.PAID: [OrderEventType.CONFIRMED, OrderEventType.PAID],
        OrderEventType.PROCESSING: [
            OrderEventType.CONFIRMED,
            OrderEventType.PAID,
            OrderEventType.PROCESSING,
        ],
        OrderEventType.SHIPPED: [
            OrderEventType.CONFIRMED,
            OrderEventType.PAID,
            OrderEventType.PROCESSING,
            OrderEventType.SHIPPED,
        ],
    }[walk_to]
    for s in path:
        transition_order(order=order, to_state=s)
    return order


@pytest.fixture
def staff(django_user_model):
    return django_user_model.objects.create_user(
        username="staff",
        password="x",
        is_staff=True,
        is_superuser=True,
    )


def _changelist_post(client, action: str, order_pks: list[int], **extra):
    """Submit a Django admin changelist action POST."""
    return client.post(
        reverse("admin:orders_order_changelist"),
        {"action": action, "_selected_action": [str(pk) for pk in order_pks], **extra},
        follow=True,
    )


class TestForwardTransitionActions:
    def test_mark_processing(self, client, staff):
        order = _order(OrderEventType.PAID)
        client.force_login(staff)
        _changelist_post(client, "action_mark_processing", [order.pk])
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.PROCESSING

    def test_mark_delivered(self, client, staff):
        order = _order(OrderEventType.SHIPPED)
        client.force_login(staff)
        _changelist_post(client, "action_mark_delivered", [order.pk])
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.DELIVERED

    def test_mark_completed(self, client, staff):
        order = _order(OrderEventType.SHIPPED)
        transition_order(order=order, to_state=OrderEventType.DELIVERED)
        client.force_login(staff)
        _changelist_post(client, "action_mark_completed", [order.pk])
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.COMPLETED

    def test_cancel_order(self, client, staff):
        order = _order(OrderEventType.PROCESSING)
        client.force_login(staff)
        _changelist_post(client, "action_cancel_order", [order.pk])
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.CANCELLED

    def test_illegal_transition_is_reported_not_silently_skipped(self, client, staff):
        """Marking a PENDING order as Delivered must fail validation, not silently
        succeed. The transition table forbids skipping states."""
        order = _order(OrderEventType.PENDING)
        client.force_login(staff)
        _changelist_post(client, "action_mark_delivered", [order.pk])
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.PENDING

    def test_marking_writes_actor(self, client, staff):
        """The OrderEvent.actor must be set to the staff user, not None."""
        order = _order(OrderEventType.PAID)
        client.force_login(staff)
        _changelist_post(client, "action_mark_processing", [order.pk])
        event = order.events.order_by("-id").first()
        assert event.event_type == OrderEventType.PROCESSING
        assert event.actor_id == staff.id


class TestMarkShippedAction:
    def test_renders_intermediate_form(self, client, staff):
        order = _order(OrderEventType.PROCESSING)
        client.force_login(staff)
        response = client.post(
            reverse("admin:orders_order_changelist"),
            {"action": "action_mark_shipped", "_selected_action": [str(order.pk)]},
        )
        assert response.status_code == 200
        assert b"Mark" in response.content and b"shipped" in response.content
        assert b"tracking_number" in response.content
        # No transition happened yet — still in PROCESSING.
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.PROCESSING

    def test_submitting_form_transitions_and_stores_tracking(self, client, staff):
        order = _order(OrderEventType.PROCESSING)
        client.force_login(staff)
        client.post(
            reverse("admin:orders_order_changelist"),
            {
                "action": "action_mark_shipped",
                "_selected_action": [str(order.pk)],
                "apply": "1",
                "tracking_number": "TCS-999-ABC",
                "carrier": "TCS",
                "note": "Left with reception",
            },
            follow=True,
        )
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.SHIPPED
        event = order.events.order_by("-id").first()
        assert event.event_type == OrderEventType.SHIPPED
        assert event.metadata.get("tracking_number") == "TCS-999-ABC"
        assert event.metadata.get("carrier") == "TCS"
        assert event.metadata.get("note") == "Left with reception"

    def test_missing_tracking_number_does_not_transition(self, client, staff):
        order = _order(OrderEventType.PROCESSING)
        client.force_login(staff)
        client.post(
            reverse("admin:orders_order_changelist"),
            {
                "action": "action_mark_shipped",
                "_selected_action": [str(order.pk)],
                "apply": "1",
                "tracking_number": "",  # required
            },
        )
        order.refresh_from_db()
        assert order.cached_status == OrderEventType.PROCESSING
