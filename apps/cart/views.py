from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import View

from apps.cart.models import CartItem
from apps.cart.selectors import get_cart_for_request, get_cart_summary
from apps.cart.services import (
    add_item,
    clear_cart,
    get_or_create_cart,
    remove_item,
    update_quantity,
)
from apps.products.models import Product, ProductVariant


class CartDetailView(View):
    template_name = "cart/cart_detail.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        cart = get_cart_for_request(request)
        summary = get_cart_summary(cart)
        return render(request, self.template_name, {"summary": summary})


@require_POST
def cart_add(request: HttpRequest) -> HttpResponse:
    try:
        product = Product.objects.get(pk=request.POST.get("product_id"))
    except (Product.DoesNotExist, ValueError, TypeError):
        raise Http404("Product not found")

    variant = None
    if request.POST.get("variant_id"):
        variant = ProductVariant.objects.filter(pk=request.POST["variant_id"]).first()

    try:
        quantity = int(request.POST.get("quantity", "1"))
    except (TypeError, ValueError):
        quantity = 1

    cart = get_or_create_cart(request)
    try:
        add_item(cart=cart, product=product, variant=variant, quantity=quantity)
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
        return HttpResponseRedirect(product.get_absolute_url())

    messages.success(request, f"Added {product.name} to cart.")
    # Honour 'next' param so the user stays on the product page if they want.
    return HttpResponseRedirect(request.POST.get("next") or reverse("cart:detail"))


@require_POST
def cart_update(request: HttpRequest, item_id: int) -> HttpResponse:
    cart = get_cart_for_request(request)
    if cart is None:
        raise Http404("Cart not found")
    item = CartItem.objects.filter(pk=item_id, cart=cart).first()
    if item is None:
        raise Http404("Item not found")
    try:
        quantity = int(request.POST.get("quantity", "1"))
    except (TypeError, ValueError):
        quantity = 1
    try:
        update_quantity(item=item, quantity=quantity)
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
    return HttpResponseRedirect(reverse("cart:detail"))


@require_POST
def cart_remove(request: HttpRequest, item_id: int) -> HttpResponse:
    cart = get_cart_for_request(request)
    if cart is None:
        raise Http404("Cart not found")
    item = CartItem.objects.filter(pk=item_id, cart=cart).first()
    if item is None:
        raise Http404("Item not found")
    remove_item(item=item)
    return HttpResponseRedirect(reverse("cart:detail"))


@require_POST
def cart_clear(request: HttpRequest) -> HttpResponse:
    cart = get_cart_for_request(request)
    if cart is not None:
        clear_cart(cart=cart)
    return HttpResponseRedirect(reverse("cart:detail"))


@require_GET
def cart_fragment(request: HttpRequest) -> HttpResponse:
    """
    Returns just the mini-cart drawer markup — for JS refresh after add-to-cart.
    Static HTML, no JS dependency: a `<script>` snippet at the bottom can re-fetch
    this and swap into the drawer container without a full page reload.
    """
    cart = get_cart_for_request(request)
    summary = get_cart_summary(cart)
    return render(request, "cart/_mini_cart.html", {"summary": summary})
