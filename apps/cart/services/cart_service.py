from __future__ import annotations

from django.db import transaction
from django.http import HttpRequest

from apps.cart.models import Cart, CartItem
from apps.cart.validators import (
    validate_product_purchasable,
    validate_quantity_bounds,
    validate_stock_available,
)
from apps.products.models import Product, ProductVariant


def get_or_create_cart(request: HttpRequest) -> Cart:
    """Return the active cart for this request — user-bound if logged in, else session-bound."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    if not request.session.session_key:
        request.session.save()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


@transaction.atomic
def add_item(
    *,
    cart: Cart,
    product: Product,
    quantity: int,
    variant: ProductVariant | None = None,
) -> CartItem:
    validate_product_purchasable(product)
    if variant and not variant.is_active:
        from django.core.exceptions import ValidationError

        raise ValidationError("Variant is not available.")

    item, created = CartItem.objects.select_for_update().get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={"quantity": quantity},
    )
    if not created:
        item.quantity += quantity

    validate_quantity_bounds(product=product, quantity=item.quantity)
    validate_stock_available(product=product, quantity=item.quantity)
    item.save(update_fields=["quantity", "updated_at"])
    cart.save(update_fields=["updated_at"])
    return item


@transaction.atomic
def update_quantity(*, item: CartItem, quantity: int) -> CartItem:
    if quantity <= 0:
        item.delete()
        return item
    validate_quantity_bounds(product=item.product, quantity=quantity)
    validate_stock_available(product=item.product, quantity=quantity)
    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])
    item.cart.save(update_fields=["updated_at"])
    return item


@transaction.atomic
def remove_item(*, item: CartItem) -> None:
    cart = item.cart
    item.delete()
    cart.save(update_fields=["updated_at"])  # bumps via auto_now=True


@transaction.atomic
def clear_cart(*, cart: Cart) -> None:
    cart.items.all().delete()
    cart.save(update_fields=["updated_at"])


@transaction.atomic
def merge_session_cart_into_user_cart(*, session_key: str, user) -> Cart:
    """Called from a login signal. Additive merge, dedup by (product, variant)."""
    try:
        session_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
    except Cart.DoesNotExist:
        return Cart.objects.get_or_create(user=user)[0]

    user_cart, _ = Cart.objects.get_or_create(user=user)
    for src in session_cart.items.all():
        existing = user_cart.items.filter(product=src.product, variant=src.variant).first()
        if existing:
            existing.quantity += src.quantity
            existing.save(update_fields=["quantity", "updated_at"])
        else:
            CartItem.objects.create(
                cart=user_cart,
                product=src.product,
                variant=src.variant,
                quantity=src.quantity,
            )
    session_cart.delete()
    user_cart.save(update_fields=["updated_at"])
    return user_cart
