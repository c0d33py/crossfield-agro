from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from apps.cart.models import Cart
from apps.orders.models import Order
from apps.orders.services import create_order_from_cart
from apps.payments.gateways import IntentResponse
from apps.payments.services import create_payment_intent


@dataclass(frozen=True)
class CheckoutResult:
    order: Order
    intent: IntentResponse


@transaction.atomic
def place_order(
    *,
    cart: Cart,
    email: str,
    shipping_address: dict,
    billing_address: dict,
    gateway_name: str,
    user=None,
    shipping_total: Decimal = Decimal("0.00"),
    tax_total: Decimal = Decimal("0.00"),
    discount_total: Decimal = Decimal("0.00"),
) -> CheckoutResult:
    """
    Orchestrates: create order from cart -> create payment intent.
    Both inside one transaction so we never have an order without an intent.
    """
    order = create_order_from_cart(
        cart=cart,
        email=email,
        shipping_address=shipping_address,
        billing_address=billing_address,
        shipping_total=shipping_total,
        tax_total=tax_total,
        discount_total=discount_total,
        user=user,
    )
    intent = create_payment_intent(order=order, gateway_name=gateway_name)
    return CheckoutResult(order=order, intent=intent)
