from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from django_ratelimit.decorators import ratelimit

from apps.orders.forms import OrderTrackForm
from apps.orders.models import OrderEventType
from apps.orders.selectors import (
    get_order_by_number,
    get_order_by_uuid,
    get_order_for_user,
    get_user_orders,
)


def _resolve_order(request: HttpRequest, order_uuid):
    """
    UUID is the secret. Logged-in user can only access their own orders.
    Anonymous users can access any order if they have the UUID (post-checkout flow).
    """
    if request.user.is_authenticated:
        order = get_order_for_user(user=request.user, order_uuid=order_uuid)
        if order is not None:
            return order
        # Fall through to anonymous lookup so admins / guest-checkout buyers
        # can still view the order via the link the system gives them.
    return get_order_by_uuid(order_uuid)


@method_decorator(login_required, name="dispatch")
class OrderListView(View):
    template_name = "orders/order_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        orders = get_user_orders(request.user)
        return render(request, self.template_name, {"orders": orders})


class OrderDetailView(View):
    template_name = "orders/order_detail.html"

    def get(self, request: HttpRequest, order_uuid) -> HttpResponse:
        order = _resolve_order(request, order_uuid)
        if order is None:
            raise Http404("Order not found")
        return render(request, self.template_name, {"order": order})


class OrderConfirmationView(View):
    """
    Post-payment success page. Shown once the order is PAID (or beyond) —
    if not yet PAID, sends the user back to the checkout return page to keep polling.
    """

    template_name = "orders/order_confirmation.html"

    def get(self, request: HttpRequest, order_uuid) -> HttpResponse:
        order = _resolve_order(request, order_uuid)
        if order is None:
            raise Http404("Order not found")

        status = order.current_status
        # COD orders start PENDING (awaiting staff call-back) and settle payment
        # at delivery — both PENDING and CONFIRMED are valid "show confirmation"
        # states for them. Prepaid CONFIRMED means "awaiting webhook" -> poll.
        cod_payment = order.payments.filter(gateway="cod").exists()
        terminal_or_paid = status in {
            OrderEventType.PAID,
            OrderEventType.PROCESSING,
            OrderEventType.SHIPPED,
            OrderEventType.DELIVERED,
            OrderEventType.COMPLETED,
        } or (cod_payment and status in {OrderEventType.PENDING, OrderEventType.CONFIRMED})
        if not terminal_or_paid:
            from django.http import HttpResponseRedirect
            from django.urls import reverse

            return HttpResponseRedirect(
                reverse("checkout:return", kwargs={"order_uuid": order.uuid})
            )

        invoice = getattr(order, "invoice", None)
        return render(
            request,
            self.template_name,
            {
                "order": order,
                "invoice": invoice,
                "is_cod": cod_payment,
            },
        )


class OrderStatusView(View):
    """JSON endpoint polled by checkout-return page during payment confirmation."""

    def get(self, request: HttpRequest, order_uuid) -> JsonResponse:
        order = _resolve_order(request, order_uuid)
        if order is None:
            raise Http404("Order not found")
        return JsonResponse({"number": order.number, "status": order.current_status})


@method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True), name="post")
class OrderTrackView(View):
    """
    Public order tracking — order number only. Rate-limited (10/min/IP on POST)
    to defeat brute-force enumeration of the 6-hex-char order number suffix
    per .claude/rules/security.md.
    """

    template_name = "orders/order_track.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": OrderTrackForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = OrderTrackForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        order = get_order_by_number(number=form.cleaned_data["order_number"])
        if order is None:
            form.add_error(None, "We couldn't find an order with that number.")
            return render(request, self.template_name, {"form": form})

        return HttpResponseRedirect(
            reverse("orders:track-detail", kwargs={"order_number": order.number})
        )


@method_decorator(ratelimit(key="ip", rate="60/m", method="GET", block=True), name="get")
class OrderTrackDetailView(View):
    """
    Read-only public status page. Exposes order number, status, timeline (with
    tracking number when SHIPPED). Deliberately omits line items, prices, and
    addresses — order number alone is too weak to gate those.
    """

    template_name = "orders/order_track_detail.html"

    def get(self, request: HttpRequest, order_number: str) -> HttpResponse:
        order = get_order_by_number(number=order_number)
        if order is None:
            raise Http404("Order not found")

        events = list(order.events.all())
        shipped_event = next((e for e in events if e.event_type == OrderEventType.SHIPPED), None)
        tracking = (shipped_event.metadata or {}) if shipped_event else {}
        return render(
            request,
            self.template_name,
            {
                "order": order,
                "events": events,
                "tracking_number": tracking.get("tracking_number", ""),
                "carrier": tracking.get("carrier", ""),
            },
        )
