from __future__ import annotations

from django.db.models import QuerySet

from apps.shipping.models import ShippingMethod, ShippingRate


def get_active_methods() -> QuerySet[ShippingMethod]:
    return ShippingMethod.objects.filter(is_active=True).order_by("position", "name")


def get_rates_for_method(method: ShippingMethod) -> QuerySet[ShippingRate]:
    return method.rates.all().order_by("country", "min_weight_kg")
