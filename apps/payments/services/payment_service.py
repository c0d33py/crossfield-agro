"""
Payment services. Implements the webhook lifecycle described in
.claude/workflows/payment-handling.md.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.orders.models import Order, OrderEventType
from apps.orders.services import transition_order

# import adapters so they register themselves
from apps.payments.gateways import (  # noqa: F401
    GatewayEvent,
    IntentResponse,
    bank_transfer,
    cod,
    get_gateway,
)
from apps.payments.models import Payment, PaymentEvent, PaymentStatus

logger = logging.getLogger(__name__)


@transaction.atomic
def create_payment_intent(*, order: Order, gateway_name: str) -> IntentResponse:
    """Server-authoritative: amount comes from the order, NOT from the client."""
    gateway = get_gateway(gateway_name)
    site = getattr(settings, "SITE_DOMAIN", "localhost")
    scheme = getattr(settings, "SITE_SCHEME", "https")
    return_url = f"{scheme}://{site}{reverse('checkout:return', args=[order.uuid])}"
    webhook_url = f"{scheme}://{site}{reverse('payments:webhook', args=[gateway_name])}"

    response = gateway.create_intent(
        amount=order.grand_total,
        currency=order.currency,
        reference=order.number,
        return_url=return_url,
        webhook_url=webhook_url,
    )

    Payment.objects.create(
        order=order,
        gateway=gateway_name,
        gateway_intent_id=response.intent_id,
        amount=order.grand_total,
        currency=order.currency,
        status=PaymentStatus.INITIATED,
    )

    # All gateways advance to CONFIRMED at intent creation. For COD this also
    # decrements stock here (the COD equivalent of "payment confirmation" for
    # stock-decrement timing). The admin confirm_cod_order action is preserved
    # for re-confirmations / manual recovery but is a no-op in the normal flow.
    transition_order(order=order, to_state=OrderEventType.CONFIRMED)

    if gateway_name == "cod":
        from apps.products.services import InsufficientStock, decrement_stock_for_order

        try:
            decrement_stock_for_order(order=order)
        except InsufficientStock as exc:
            # Roll back the whole intent: order is in @transaction.atomic.
            from django.core.exceptions import ValidationError

            raise ValidationError(f"Cannot fulfill order: {exc}") from exc

    return response


@transaction.atomic
def confirm_cod_order(*, order: Order, actor=None) -> Order:
    """
    Recovery action: confirm a COD order that's stuck in PENDING for any
    reason (data fix, partial failure, manual import). Normal COD orders
    auto-confirm at checkout via create_payment_intent — this is a no-op
    for them.

    Idempotent + race-safe: locks the order row, re-reads status from the
    event log, and no-ops if the order is already past PENDING.
    """
    # Lock the order row so concurrent admin actions can't both pass the
    # PENDING check and double-confirm + double-decrement stock.
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.current_status != OrderEventType.PENDING:
        return locked

    transition_order(order=locked, to_state=OrderEventType.CONFIRMED, actor=actor)

    from apps.products.services import InsufficientStock, decrement_stock_for_order

    try:
        decrement_stock_for_order(order=locked)
    except InsufficientStock as exc:
        from django.core.exceptions import ValidationError

        raise ValidationError(f"Cannot confirm order: {exc}") from exc
    return locked


@transaction.atomic
def mark_cod_received(*, order: Order, actor=None) -> Payment:
    """
    Staff records that the courier has collected the COD cash. Flips Payment
    to SUCCEEDED, writes an audit entry, and queues the invoice. Order state
    is independent — typically DELIVERED already; we do NOT transition it.
    """
    payment = (
        Payment.objects.select_for_update()
        .filter(order=order, gateway="cod")
        .order_by("-created_at")
        .first()
    )
    if payment is None:
        from django.core.exceptions import ValidationError

        raise ValidationError(f"No COD payment found on order {order.number}.")
    if payment.status == PaymentStatus.SUCCEEDED:
        return payment  # idempotent

    payment.status = PaymentStatus.SUCCEEDED
    payment.save(update_fields=["status", "updated_at"])

    try:
        from apps.audit.models import AuditAction
        from apps.audit.services import log_action

        log_action(
            action=AuditAction.PAYMENT_RECEIVED,
            actor=actor,
            target=payment,
            description=f"COD cash received for {order.number}",
            metadata={"amount": str(payment.amount), "gateway": "cod"},
        )
    except Exception:
        pass

    # NB: invoice was already issued at order CONFIRMED — see
    # apps.orders.services.transition_order. Nothing to enqueue here.
    return payment


def handle_webhook(*, gateway_name: str, payload: bytes, signature: str) -> PaymentEvent:
    """
    Verify signature, dedupe by event_id, then process inside transaction.
    Returns the persisted PaymentEvent (existing if duplicate).
    """
    gateway = get_gateway(gateway_name)
    gateway.verify_signature(payload, signature)
    event = gateway.parse(payload)

    existing = PaymentEvent.objects.filter(
        gateway=gateway_name, gateway_event_id=event.event_id
    ).first()
    if existing is not None:
        logger.info("Duplicate webhook %s:%s ignored", gateway_name, event.event_id)
        return existing

    with transaction.atomic():
        record = PaymentEvent.objects.create(
            gateway=gateway_name,
            gateway_event_id=event.event_id,
            event_type=event.type,
            raw_payload=payload.decode("utf-8", errors="replace"),
        )
        payment = Payment.objects.select_for_update().get(gateway_intent_id=event.intent_id)
        record.payment = payment
        record.save(update_fields=["payment"])

        if event.type == "payment.succeeded":
            _mark_paid(payment)
        elif event.type == "payment.failed":
            _mark_failed(payment, reason=event.failure_reason)
        else:
            logger.info("Unhandled webhook type %s for %s", event.type, payment.id)

    return record


def _mark_paid(payment: Payment) -> None:
    if payment.status == PaymentStatus.SUCCEEDED:
        return  # defence in depth
    payment.status = PaymentStatus.SUCCEEDED
    payment.save(update_fields=["status", "updated_at"])
    transition_order(order=payment.order, to_state=OrderEventType.PAID)

    # Decrement inventory per .claude/rules/commerce-rules.md
    # ("Stock decrement happens at payment confirmation"). Atomic + row-locked.
    from apps.products.services import InsufficientStock, decrement_stock_for_order

    try:
        decrement_stock_for_order(order=payment.order)
    except InsufficientStock as exc:
        logger.error(
            "Insufficient stock for paid order %s: %s — manual intervention required",
            payment.order.number,
            exc,
        )
        # Don't raise: the payment is real, the order is PAID. Ops needs to fulfil
        # via emergency stock / partial shipment / customer comms. Surface via audit.
        try:
            from apps.audit.models import AuditAction
            from apps.audit.services import log_action

            log_action(
                action=AuditAction.OTHER,
                target=payment.order,
                description=f"PAID but insufficient stock: {exc}",
                metadata={"alert": "manual_fulfillment_required"},
            )
        except Exception:
            pass

    # Audit
    try:
        from apps.audit.models import AuditAction
        from apps.audit.services import log_action

        log_action(
            action=AuditAction.PAYMENT_RECEIVED,
            target=payment,
            description=f"Payment {payment.gateway_intent_id} succeeded for {payment.order.number}",
            metadata={"amount": str(payment.amount), "gateway": payment.gateway},
        )
    except Exception:
        pass

    # Dispatch side effects via Celery — never inline. Invoice was issued at
    # order CONFIRMED via transition_order; the PDF re-render task below
    # refreshes it to a tax-invoice header now that payment has cleared.
    from apps.invoices.models import Invoice
    from apps.invoices.tasks import render_invoice_pdf
    from apps.orders.tasks import send_order_confirmation

    send_order_confirmation.delay(payment.order_id)
    invoice = Invoice.objects.filter(order=payment.order).first()
    if invoice is not None:
        render_invoice_pdf.delay(invoice.pk)


def _mark_failed(payment: Payment, *, reason: str) -> None:
    if payment.status == PaymentStatus.FAILED:
        return
    payment.status = PaymentStatus.FAILED
    payment.save(update_fields=["status", "updated_at"])
    transition_order(
        order=payment.order,
        to_state=OrderEventType.PAYMENT_FAILED,
        metadata={"reason": reason},
    )

    # Audit
    try:
        from apps.audit.models import AuditAction
        from apps.audit.services import log_action

        log_action(
            action=AuditAction.PAYMENT_FAILED,
            target=payment,
            description=f"Payment {payment.gateway_intent_id} failed: {reason}",
            metadata={"reason": reason, "gateway": payment.gateway},
        )
    except Exception:
        pass


def reconcile_pending_payments(*, older_than_hours: int = 1) -> int:
    """
    Hourly Beat job. For any Payment stuck INITIATED past the threshold, ask
    the gateway for its terminal status and replay through handle_webhook
    via a synthetic event.
    """
    cutoff = timezone.now() - timezone.timedelta(hours=older_than_hours)
    stuck = Payment.objects.filter(status=PaymentStatus.INITIATED, created_at__lt=cutoff)
    reconciled = 0
    for payment in stuck:
        try:
            gw = get_gateway(payment.gateway)
            status = gw.fetch_status(payment.gateway_intent_id)
            if not status.is_terminal:
                continue
            with transaction.atomic():
                payment.refresh_from_db()
                if status.succeeded:
                    _mark_paid(payment)
                else:
                    _mark_failed(payment, reason="reconciliation: gateway reported failure")
            reconciled += 1
        except Exception:
            logger.exception("reconcile_pending_payments failed for %s", payment.id)
    return reconciled
