from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ProductValidationError(ValidationError):
    pass


def validate_price(price: Decimal) -> None:
    if price is None or price < Decimal("0.00"):
        raise ProductValidationError(_("Price must be a non-negative decimal."))


def validate_sku(sku: str) -> None:
    if not sku or not sku.strip():
        raise ProductValidationError(_("SKU is required."))
    if len(sku) > 64:
        raise ProductValidationError(_("SKU must be 64 characters or fewer."))
    if " " in sku:
        raise ProductValidationError(_("SKU must not contain spaces."))


def validate_stock_quantity(qty: int) -> None:
    if qty is None or qty < 0:
        raise ProductValidationError(_("Stock quantity must be zero or positive."))


def validate_order_quantity_bounds(*, min_qty: int, max_qty: int | None) -> None:
    if min_qty < 1:
        raise ProductValidationError(_("min_order_quantity must be at least 1."))
    if max_qty is not None and max_qty < min_qty:
        raise ProductValidationError(
            _("max_order_quantity must be greater than or equal to min_order_quantity.")
        )


def validate_seo_title(value: str) -> None:
    if value and len(value) > 70:
        raise ProductValidationError(_("SEO title should be 70 characters or fewer."))


def validate_seo_description(value: str) -> None:
    if value and len(value) > 170:
        raise ProductValidationError(_("SEO description should be 170 characters or fewer."))
