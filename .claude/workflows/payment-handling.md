# Payment Handling Workflow

## Principles

- **The webhook is the source of truth.** Not the redirect, not the gateway API response from the intent call.
- **Idempotency is mandatory.** Webhooks can fire twice (or more).
- **Server-side everything.** Frontend never sees the amount it can mutate.

## Lifecycle

```text
[1] CREATE_INTENT   →  Payment.status = INITIATED
[2] USER_PAYS       →  Gateway-hosted; nothing happens server-side
[3] REDIRECT_BACK   →  Show "Processing"; do NOT mark paid
[4] WEBHOOK         →  Verify → Persist event → Update state (atomic)
[5] CONFIRMATION    →  Order PAID; email + invoice (async)
```

## Step 1 — Create Intent

```python
def create_payment_intent(*, order: Order) -> PaymentIntent:
    """Server-side call to gateway. Server owns the amount."""
    amount = order.grand_total_in_minor_units  # already computed at order creation
    response = gateway.create_intent(
        amount=amount,
        currency=order.currency,
        reference=str(order.id),
        webhook_url=settings.PAYMENT_WEBHOOK_URL,
        return_url=settings.PAYMENT_RETURN_URL,
    )
    Payment.objects.create(
        order=order,
        gateway=response.gateway,
        gateway_intent_id=response.intent_id,
        amount=amount,
        status=PaymentStatus.INITIATED,
    )
    return PaymentIntent(redirect_url=response.redirect_url, token=response.client_token)
```

## Step 2 — User Pays

Nothing happens server-side. The gateway hosts the card form.

## Step 3 — Redirect Back

```python
def payment_return_view(request, order_id):
    """User UX only. Never updates order state. Polls / shows status."""
    order = get_order_for_user(request.user, order_id)
    return render(request, "checkout/return.html", {"order": order})
    # Template polls /orders/<id>/status/ every 2s until PAID or FAILED
```

## Step 4 — Webhook (CRITICAL)

```python
@csrf_exempt
@require_POST
def webhook_view(request, gateway_name):
    payload = request.body
    signature = request.headers.get("X-Gateway-Signature", "")

    try:
        event = handle_webhook(
            gateway=gateway_name,
            payload=payload,
            signature=signature,
        )
    except WebhookSignatureError:
        return HttpResponse(status=401)
    except WebhookParseError:
        return HttpResponse(status=400)

    return HttpResponse(status=200)


def handle_webhook(*, gateway: str, payload: bytes, signature: str) -> PaymentEvent:
    gw = get_gateway(gateway)
    gw.verify_signature(payload, signature)          # raises on mismatch
    event_data = gw.parse(payload)

    # IDEMPOTENCY: short-circuit if we've seen this event
    existing = PaymentEvent.objects.filter(
        gateway=gateway, gateway_event_id=event_data.event_id
    ).first()
    if existing:
        return existing

    with transaction.atomic():
        # Persist raw event FIRST (audit trail even if downstream fails)
        event = PaymentEvent.objects.create(
            gateway=gateway,
            gateway_event_id=event_data.event_id,
            event_type=event_data.type,
            raw_payload=payload.decode("utf-8"),
        )

        payment = Payment.objects.select_for_update().get(
            gateway_intent_id=event_data.intent_id
        )

        if event_data.type == "payment.succeeded":
            _mark_paid(payment)
        elif event_data.type == "payment.failed":
            _mark_failed(payment, reason=event_data.failure_reason)
        # else: log and ignore

    return event


def _mark_paid(payment: Payment) -> None:
    if payment.status == PaymentStatus.SUCCEEDED:
        return  # already processed (defense in depth)

    payment.status = PaymentStatus.SUCCEEDED
    payment.save(update_fields=["status", "updated_at"])

    OrderEvent.objects.create(order=payment.order, event_type=OrderEventType.PAID)
    decrement_stock_for_order(payment.order)
    release_reservation_for_order(payment.order)

    send_order_confirmation.delay(payment.order.id)
    generate_invoice.delay(payment.order.id)
```

## Step 5 — Confirmation

- Frontend polling sees `Order.current_status == PAID`
- Redirects to confirmation page
- Email already in flight via Celery
- Invoice generation in flight via Celery

## Reconciliation Job (Safety Net)

If a webhook never arrives:

```python
@shared_task
def reconcile_pending_payments():
    """Hourly: query gateway for any Payment stuck in INITIATED > 1h."""
    cutoff = timezone.now() - timedelta(hours=1)
    stuck = Payment.objects.filter(status=PaymentStatus.INITIATED, created_at__lt=cutoff)
    for payment in stuck:
        gw_status = get_gateway(payment.gateway).fetch_status(payment.gateway_intent_id)
        if gw_status.is_terminal:
            # Construct a synthetic webhook event and process via the same path
            handle_synthetic_event(payment, gw_status)
```

## Refunds

- Refund is a NEW `Payment` row (negative amount) linked to the original
- Requires staff role + reason
- Submits to gateway; awaits webhook confirmation
- On success: append `OrderEvent(REFUNDED)` (partial or full)
- Audit entry recorded

## Common Mistakes to Avoid

- ❌ Marking order paid in the return URL view
- ❌ Verifying signature AFTER processing
- ❌ Skipping signature verification "for testing"
- ❌ Storing webhook secret in code instead of env var
- ❌ Not handling duplicate webhooks (idempotency missing)
- ❌ Updating order status outside a transaction
- ❌ Calling email send / PDF gen synchronously inside the webhook handler
