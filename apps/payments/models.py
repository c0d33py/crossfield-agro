"""
Payments. Critical rules (.claude/rules/commerce-rules.md, payment-handling.md):

- Webhook is the source of truth (NOT the redirect-back).
- Idempotency via PaymentEvent.gateway_event_id unique constraint.
- HMAC signature verified on every webhook before processing.
- Raw payload persisted for audit trail.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentStatus(models.TextChoices):
    INITIATED = "initiated", _("Initiated")
    SUCCEEDED = "succeeded", _("Succeeded")
    FAILED = "failed", _("Failed")
    REFUNDED = "refunded", _("Refunded")


class Gateway(models.TextChoices):
    JAZZCASH = "jazzcash", _("JazzCash")
    EASYPAISA = "easypaisa", _("EasyPaisa")
    HBL = "hbl", _("HBL")
    MEEZAN = "meezan", _("MeezanPay")
    BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
    COD = "cod", _("Cash on Delivery")


class Payment(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        related_name="payments",
        on_delete=models.PROTECT,
    )
    gateway = models.CharField(max_length=24, choices=Gateway.choices)
    gateway_intent_id = models.CharField(max_length=128, unique=True, db_index=True)

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="PKR")

    status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.INITIATED,
        db_index=True,
    )

    # For refunds — links back to the original payment row
    refund_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="refunds",
        on_delete=models.PROTECT,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.gateway} {self.gateway_intent_id} ({self.status})"


class PaymentEvent(models.Model):
    """
    Append-only log of every gateway webhook event. Unique on
    (gateway, gateway_event_id) for idempotency.
    """

    gateway = models.CharField(max_length=24, choices=Gateway.choices)
    gateway_event_id = models.CharField(max_length=128, db_index=True)
    event_type = models.CharField(max_length=64)

    payment = models.ForeignKey(
        Payment, related_name="events", null=True, blank=True, on_delete=models.SET_NULL
    )

    raw_payload = models.TextField(help_text=_("Verbatim webhook body. Do NOT log card data."))

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["gateway", "gateway_event_id"],
                name="payment_event_unique_per_gateway",
            ),
        ]
        indexes = [models.Index(fields=["gateway", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.gateway}:{self.gateway_event_id}"
