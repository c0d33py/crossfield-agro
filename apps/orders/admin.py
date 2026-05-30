from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import render

from apps.orders.models import Order, OrderEvent, OrderEventType, OrderItem
from apps.orders.services import transition_order
from apps.payments.services import confirm_cod_order


class _ShippingDetailsForm(forms.Form):
    """Collected once for a batch Mark-Shipped action."""

    tracking_number = forms.CharField(max_length=64, required=True, label="Tracking number")
    carrier = forms.CharField(max_length=64, required=False, label="Carrier (optional)")
    note = forms.CharField(
        max_length=200,
        required=False,
        label="Internal note (optional)",
        widget=forms.Textarea(attrs={"rows": 2}),
    )


def _bulk_transition(
    self, request, queryset, *, to_state: str, label: str, metadata: dict | None = None
):
    """Shared helper: apply a forward transition to every order in the queryset.
    Routes through transition_order so ALLOWED_TRANSITIONS, audit log, and the
    cached_status update all happen correctly. Reports per-order failures."""
    applied = 0
    failed = []
    for order in queryset:
        try:
            transition_order(order=order, to_state=to_state, actor=request.user, metadata=metadata)
            applied += 1
        except ValidationError as exc:
            failed.append(f"{order.number}: {'; '.join(exc.messages)}")
    if applied:
        self.message_user(request, f"{applied} order(s) marked {label}.", messages.SUCCESS)
    for msg in failed:
        self.message_user(request, msg, messages.ERROR)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product_name", "sku", "unit_price", "quantity", "line_total")
    fields = readonly_fields
    raw_id_fields = ("product", "variant")


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    readonly_fields = ("event_type", "created_at", "actor", "metadata")
    fields = readonly_fields


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "user",
        "email",
        "currency",
        "grand_total",
        "cached_status",
        "created_at",
    )
    list_filter = ("cached_status", "currency", "created_at")
    search_fields = ("number", "uuid", "email", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = (
        "uuid",
        "number",
        "subtotal",
        "shipping_total",
        "tax_total",
        "discount_total",
        "grand_total",
        "currency",
        "shipping_address",
        "billing_address",
        "created_at",
        "cached_status",
    )
    inlines = [OrderItemInline, OrderEventInline]
    date_hierarchy = "created_at"
    actions = [
        "action_confirm_cod_order",
        "action_mark_processing",
        "action_mark_shipped",
        "action_mark_delivered",
        "action_mark_completed",
        "action_cancel_order",
    ]

    # --- COD-specific (existing) ---------------------------------------
    @admin.action(description="Confirm COD order (after customer call-back)")
    def action_confirm_cod_order(self, request, queryset):
        confirmed = 0
        skipped = 0
        failed = []
        for order in queryset:
            if order.cached_status != OrderEventType.PENDING:
                skipped += 1
                continue
            if not order.payments.filter(gateway="cod").exists():
                skipped += 1
                continue
            try:
                confirm_cod_order(order=order, actor=request.user)
                confirmed += 1
            except ValidationError as exc:
                failed.append(f"{order.number}: {'; '.join(exc.messages)}")
        if confirmed:
            self.message_user(request, f"{confirmed} COD order(s) confirmed.", messages.SUCCESS)
        if skipped:
            self.message_user(
                request, f"{skipped} skipped (not PENDING or not COD).", messages.WARNING
            )
        for msg in failed:
            self.message_user(request, msg, messages.ERROR)

    # --- Forward transitions (new) -------------------------------------
    # Each appends a new OrderEvent via transition_order — never mutates the
    # event log. Validation (ALLOWED_TRANSITIONS) lives in the service.

    @admin.action(description="Mark as Processing (begin fulfillment)")
    def action_mark_processing(self, request, queryset):
        _bulk_transition(
            self, request, queryset, to_state=OrderEventType.PROCESSING, label="processing"
        )

    @admin.action(description="Mark as Shipped (will prompt for tracking number)")
    def action_mark_shipped(self, request, queryset):
        """Intermediate-page action: ask for tracking number, then transition."""
        if "apply" in request.POST:
            form = _ShippingDetailsForm(request.POST)
            if form.is_valid():
                meta = {
                    "tracking_number": form.cleaned_data["tracking_number"],
                }
                if form.cleaned_data.get("carrier"):
                    meta["carrier"] = form.cleaned_data["carrier"]
                if form.cleaned_data.get("note"):
                    meta["note"] = form.cleaned_data["note"]
                _bulk_transition(
                    self,
                    request,
                    queryset,
                    to_state=OrderEventType.SHIPPED,
                    label="shipped",
                    metadata=meta,
                )
                return None  # back to changelist
        else:
            form = _ShippingDetailsForm()

        return render(
            request,
            "admin/orders/mark_shipped.html",
            {
                "orders": queryset,
                "form": form,
                "action": "action_mark_shipped",
            },
        )

    @admin.action(description="Mark as Delivered")
    def action_mark_delivered(self, request, queryset):
        _bulk_transition(
            self, request, queryset, to_state=OrderEventType.DELIVERED, label="delivered"
        )

    @admin.action(description="Mark as Completed")
    def action_mark_completed(self, request, queryset):
        _bulk_transition(
            self, request, queryset, to_state=OrderEventType.COMPLETED, label="completed"
        )

    @admin.action(description="Cancel order")
    def action_cancel_order(self, request, queryset):
        _bulk_transition(
            self,
            request,
            queryset,
            to_state=OrderEventType.CANCELLED,
            label="cancelled",
            metadata={"reason": "staff_cancellation"},
        )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "sku", "unit_price", "quantity", "line_total")
    search_fields = ("order__number", "product_name", "sku")


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ("order", "event_type", "created_at", "actor")
    list_filter = ("event_type",)
    search_fields = ("order__number",)
    raw_id_fields = ("order", "actor")
    readonly_fields = ("order", "event_type", "created_at", "actor", "metadata")
