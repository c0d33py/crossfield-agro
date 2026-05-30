"""
Orders are IMMUTABLE. State lives in OrderEvent rows.

Reference: .claude/rules/commerce-rules.md, .claude/workflows/order-lifecycle.md
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class OrderEventType(models.TextChoices):
    PENDING = "pending", _("Pending")
    CONFIRMED = "confirmed", _("Confirmed")
    PAID = "paid", _("Paid")
    PAYMENT_FAILED = "payment_failed", _("Payment Failed")
    PROCESSING = "processing", _("Processing")
    SHIPPED = "shipped", _("Shipped")
    DELIVERED = "delivered", _("Delivered")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
    REFUNDED = "refunded", _("Refunded")


# Allowed transitions: source state -> set of legal next states
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    OrderEventType.PENDING: {
        OrderEventType.CONFIRMED,
        OrderEventType.CANCELLED,
        OrderEventType.PAYMENT_FAILED,
    },
    OrderEventType.CONFIRMED: {
        OrderEventType.PAID,
        OrderEventType.PROCESSING,
        OrderEventType.CANCELLED,
        OrderEventType.PAYMENT_FAILED,
    },
    OrderEventType.PAYMENT_FAILED: {OrderEventType.CONFIRMED, OrderEventType.CANCELLED},
    OrderEventType.PAID: {OrderEventType.PROCESSING, OrderEventType.REFUNDED},
    OrderEventType.PROCESSING: {OrderEventType.SHIPPED, OrderEventType.CANCELLED},
    OrderEventType.SHIPPED: {OrderEventType.DELIVERED},
    OrderEventType.DELIVERED: {OrderEventType.COMPLETED, OrderEventType.REFUNDED},
    OrderEventType.COMPLETED: {OrderEventType.REFUNDED},
}


class Order(models.Model):
    """Immutable header. NEVER UPDATE order.status — use OrderEvent."""

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    number = models.CharField(max_length=32, unique=True, db_index=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="orders",
        on_delete=models.PROTECT,
    )
    email = models.EmailField(help_text=_("Snapshot — may differ from user.email"))

    # Snapshotted addresses (raw text to survive address-model changes)
    shipping_address = models.JSONField()
    billing_address = models.JSONField()

    currency = models.CharField(max_length=3, default="PKR")
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    shipping_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )

    # Cached for list views — derived from OrderEvent; never the source of truth.
    cached_status = models.CharField(
        max_length=24,
        choices=OrderEventType.choices,
        default=OrderEventType.PENDING,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["cached_status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return self.number

    @property
    def current_status(self) -> str:
        latest = self.events.order_by("-created_at").first()
        return latest.event_type if latest else OrderEventType.PENDING


class OrderItem(models.Model):
    """
    Line items snapshot product data at creation time. Fields like
    product_name and unit_price are immutable — they survive renames/price changes.
    """

    order = models.ForeignKey(Order, related_name="items", on_delete=models.PROTECT)
    product = models.ForeignKey(
        "products.Product",
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text=_("Reference only — may go null if product deleted."),
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    # Snapshots — never mutated after creation
    product_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        indexes = [models.Index(fields=["order"])]


class OrderEvent(models.Model):
    """Append-only state log. Source of truth for order status."""

    order = models.ForeignKey(Order, related_name="events", on_delete=models.PROTECT)
    event_type = models.CharField(max_length=24, choices=OrderEventType.choices)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["order", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.order_id}: {self.event_type} @ {self.created_at:%Y-%m-%d %H:%M}"
