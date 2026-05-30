from django.contrib import admin, messages

from apps.payments.models import Payment, PaymentEvent, PaymentStatus
from apps.payments.services import mark_cod_received


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "gateway_intent_id",
        "gateway",
        "order",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "gateway", "currency")
    search_fields = ("gateway_intent_id", "order__number")
    raw_id_fields = ("order", "refund_of")
    readonly_fields = ("gateway_intent_id", "amount", "currency", "created_at", "updated_at")
    actions = ["action_mark_cod_received"]

    @admin.action(description="Mark COD cash as received (courier returned)")
    def action_mark_cod_received(self, request, queryset):
        applied = 0
        skipped = 0
        for payment in queryset:
            if payment.gateway != "cod":
                skipped += 1
                continue
            if payment.status == PaymentStatus.SUCCEEDED:
                skipped += 1
                continue
            mark_cod_received(order=payment.order, actor=request.user)
            applied += 1
        if applied:
            self.message_user(
                request, f"{applied} COD payment(s) marked as received.", messages.SUCCESS
            )
        if skipped:
            self.message_user(
                request, f"{skipped} skipped (not COD or already paid).", messages.WARNING
            )


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("gateway", "gateway_event_id", "event_type", "payment", "created_at")
    list_filter = ("gateway", "event_type")
    search_fields = ("gateway_event_id", "payment__gateway_intent_id")
    raw_id_fields = ("payment",)
    readonly_fields = (
        "gateway",
        "gateway_event_id",
        "event_type",
        "payment",
        "raw_payload",
        "created_at",
    )
