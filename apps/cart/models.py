"""
Cart models. Critical rules (see .claude/rules/commerce-rules.md):

- Cart belongs to session OR user (merge on login).
- CartItem stores product_id + quantity only — NO price.
- Totals are NEVER stored — always recomputed by selectors.
- Cart expires after 14 days of inactivity.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="carts",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["session_key", "-updated_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name="cart_user_or_session_required",
            ),
        ]

    def __str__(self) -> str:
        owner = self.user_id or self.session_key or "<empty>"
        return f"Cart({owner})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "products.Product",
        related_name="+",
        on_delete=models.PROTECT,
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product", "variant"],
                name="cart_unique_product_variant",
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gte=1),
                name="cart_item_quantity_at_least_one",
            ),
        ]
        indexes = [models.Index(fields=["cart", "product"])]
