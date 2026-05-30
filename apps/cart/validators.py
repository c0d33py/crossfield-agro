from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.products.models import Product, ProductStatus


class CartValidationError(ValidationError):
    pass


def validate_product_purchasable(product: Product) -> None:
    if product.status != ProductStatus.PUBLISHED:
        raise CartValidationError(_("Product is not available for purchase."))


def validate_quantity_bounds(*, product: Product, quantity: int) -> None:
    if quantity < product.min_order_quantity:
        raise CartValidationError(
            _("Minimum order quantity is %(min)d.") % {"min": product.min_order_quantity}
        )
    if product.max_order_quantity and quantity > product.max_order_quantity:
        raise CartValidationError(
            _("Maximum order quantity is %(max)d.") % {"max": product.max_order_quantity}
        )


def validate_stock_available(*, product: Product, quantity: int) -> None:
    if not product.track_inventory or product.allow_backorder:
        return
    if quantity > product.stock_quantity:
        raise CartValidationError(
            _("Only %(stock)d available in stock.") % {"stock": product.stock_quantity}
        )
