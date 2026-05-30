from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from apps.cart.selectors import get_cart_summary
from apps.cart.services import get_or_create_cart
from apps.checkout.forms import AddressForm, PaymentForm
from apps.checkout.services import place_order
from apps.orders.selectors import get_order_by_uuid, get_order_for_user

SESSION_KEY = "checkout"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _require_cart(request: HttpRequest):
    cart = get_or_create_cart(request)
    summary = get_cart_summary(cart)
    return cart, summary


def _empty_redirect():
    return HttpResponseRedirect(reverse("cart:detail"))


def _checkout_state(request: HttpRequest) -> dict:
    return request.session.get(SESSION_KEY, {})


def _save_checkout_state(request: HttpRequest, data: dict) -> None:
    request.session[SESSION_KEY] = data
    request.session.modified = True


def _clear_checkout_state(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY, None)


# ---------------------------------------------------------------------------
# 3-step checkout
# ---------------------------------------------------------------------------


class CheckoutStartView(View):
    """Entry point — redirects to step 1 (address)."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponseRedirect(reverse("checkout:address"))

    def post(self, request: HttpRequest) -> HttpResponse:
        # Backwards-compat: legacy single-page POST defers to AddressView.
        return AddressView.as_view()(request)


class AddressView(View):
    """Step 1 — collect shipping/billing addresses."""

    template_name = "checkout/step_address.html"
    step = 1

    def get(self, request: HttpRequest) -> HttpResponse:
        cart, summary = _require_cart(request)
        if not summary or not summary.lines:
            return _empty_redirect()

        existing = _checkout_state(request)
        initial = {
            "email": existing.get(
                "email", request.user.email if request.user.is_authenticated else ""
            ),
            "billing_same_as_shipping": existing.get("billing_same", True),
        }
        initial.update({f"shipping_{k}": v for k, v in existing.get("shipping", {}).items()})
        initial.update({f"billing_{k}": v for k, v in existing.get("billing", {}).items()})
        form = AddressForm(initial=initial)
        return render(
            request, self.template_name, {"form": form, "summary": summary, "step": self.step}
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        cart, summary = _require_cart(request)
        if not summary or not summary.lines:
            return _empty_redirect()

        form = AddressForm(request.POST)
        if not form.is_valid():
            return render(
                request, self.template_name, {"form": form, "summary": summary, "step": self.step}
            )

        state = _checkout_state(request)
        state.update(form.to_session())
        _save_checkout_state(request, state)
        return HttpResponseRedirect(reverse("checkout:review"))


class ReviewView(View):
    """Step 2 — show full order summary, edit links back to step 1."""

    template_name = "checkout/step_review.html"
    step = 2

    def get(self, request: HttpRequest) -> HttpResponse:
        cart, summary = _require_cart(request)
        if not summary or not summary.lines:
            return _empty_redirect()
        state = _checkout_state(request)
        if not state.get("shipping") or not state.get("email"):
            return HttpResponseRedirect(reverse("checkout:address"))
        return render(
            request, self.template_name, {"summary": summary, "checkout": state, "step": self.step}
        )


class PaymentView(View):
    """Step 3 — choose gateway, create order + payment intent."""

    template_name = "checkout/step_payment.html"
    step = 3

    def get(self, request: HttpRequest) -> HttpResponse:
        cart, summary = _require_cart(request)
        if not summary or not summary.lines:
            return _empty_redirect()
        state = _checkout_state(request)
        if not state.get("shipping") or not state.get("email"):
            return HttpResponseRedirect(reverse("checkout:address"))
        return render(
            request,
            self.template_name,
            {
                "form": PaymentForm(),
                "summary": summary,
                "checkout": state,
                "step": self.step,
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        cart, summary = _require_cart(request)
        if not summary or not summary.lines:
            return _empty_redirect()
        state = _checkout_state(request)
        if not state.get("shipping") or not state.get("email"):
            return HttpResponseRedirect(reverse("checkout:address"))

        form = PaymentForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "summary": summary,
                    "checkout": state,
                    "step": self.step,
                },
            )

        try:
            result = place_order(
                cart=cart,
                email=state["email"],
                shipping_address=state["shipping"],
                billing_address=state["billing"],
                gateway_name=form.cleaned_data["gateway"],
                user=request.user if request.user.is_authenticated else None,
            )
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "summary": summary,
                    "checkout": state,
                    "step": self.step,
                },
            )

        _clear_checkout_state(request)
        # COD has nothing async to wait for — skip the polling page and go
        # straight to the confirmation page. Prepaid gateways land on the
        # return page which polls until the webhook flips the order to PAID.
        if form.cleaned_data["gateway"] == "cod":
            return HttpResponseRedirect(
                reverse("orders:confirmation", kwargs={"order_uuid": result.order.uuid})
            )
        return HttpResponseRedirect(result.intent.redirect_url)


# ---------------------------------------------------------------------------
# Post-payment pages
# ---------------------------------------------------------------------------


class CheckoutReturnView(View):
    """Polling page shown while waiting for the gateway webhook to confirm PAID."""

    template_name = "checkout/return.html"

    def get(self, request: HttpRequest, order_uuid) -> HttpResponse:
        order = (
            get_order_for_user(user=request.user, order_uuid=order_uuid)
            if request.user.is_authenticated
            else get_order_by_uuid(order_uuid)
        )
        if order is None:
            raise Http404("Order not found")
        return render(request, self.template_name, {"order": order})
