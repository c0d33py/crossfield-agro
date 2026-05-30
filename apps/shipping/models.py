"""
Shipping methods + rate table. Tracking numbers live on OrderEvent(SHIPPED).metadata.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ShippingMethod(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self) -> str:
        return self.name


class ShippingRate(models.Model):
    """
    Simple rate table: per shipping method, per country, per weight band.
    Real life will outgrow this — extend or swap for a carrier API integration.
    """

    method = models.ForeignKey(ShippingMethod, related_name="rates", on_delete=models.CASCADE)
    country = models.CharField(max_length=2, default="PK")
    min_weight_kg = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0"))
    max_weight_kg = models.DecimalField(max_digits=8, decimal_places=3)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    currency = models.CharField(max_length=3, default="PKR")

    class Meta:
        ordering = ["country", "min_weight_kg"]
        indexes = [models.Index(fields=["method", "country", "min_weight_kg"])]
        constraints = [
            models.CheckConstraint(
                check=models.Q(max_weight_kg__gt=models.F("min_weight_kg")),
                name="shipping_rate_max_gt_min_weight",
            )
        ]

    def __str__(self) -> str:
        return f"{self.method.code}/{self.country} {self.min_weight_kg}–{self.max_weight_kg}kg = {self.currency} {self.price}"
