"""
AuditLogEntry — immutable record of every significant system action.

Per .claude/rules/security.md: "Every admin mutation logged to audit app" and
"Refunds require staff role + audit entry."

Entries are append-only — never edited or deleted via the public API. Admin
view is read-only; long-term retention is handled by ops (truncate by date).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditAction(models.TextChoices):
    # Generic CRUD
    CREATE = "create", _("Create")
    UPDATE = "update", _("Update")
    DELETE = "delete", _("Delete")
    # Auth
    LOGIN = "login", _("Login")
    LOGOUT = "logout", _("Logout")
    LOGIN_FAILED = "login_failed", _("Login failed")
    # Commerce
    ORDER_TRANSITION = "order_transition", _("Order status transition")
    PAYMENT_RECEIVED = "payment_received", _("Payment received")
    PAYMENT_FAILED = "payment_failed", _("Payment failed")
    REFUND = "refund", _("Refund issued")
    # Catalog / content
    PUBLISH = "publish", _("Publish")
    UNPUBLISH = "unpublish", _("Unpublish")
    # Admin-side
    PERMISSION_CHANGE = "permission_change", _("Permission change")
    EXPORT = "export", _("Data export")
    OTHER = "other", _("Other")


class AuditLogEntry(models.Model):
    action = models.CharField(
        max_length=32,
        choices=AuditAction.choices,
        db_index=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
        help_text=_("Who performed the action. NULL for system / anonymous."),
    )
    actor_label = models.CharField(
        max_length=200,
        blank=True,
        help_text=_(
            "Snapshot of actor identity (email/username) at log time — survives user deletion."
        ),
    )

    # Generic reference to any model (string-based to avoid FK overhead + bind issues)
    target_type = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
        help_text=_('e.g. "orders.Order" or "products.Product".'),
    )
    target_id = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text=_("Primary key (or UUID) of the target row, as a string."),
    )
    target_label = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Snapshot of the target's str() for human-readable logs."),
    )

    description = models.CharField(max_length=400, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["target_type", "target_id", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def __str__(self) -> str:
        who = self.actor_label or "system"
        what = self.target_label or self.target_type or "(no target)"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {who} {self.get_action_display()} {what}"
