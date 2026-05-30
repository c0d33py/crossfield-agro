# Prompt: Payment Integration

Use this when adding support for a new payment gateway (Stripe, JazzCash, EasyPaisa,
HBL, MeezanPay, bank transfer, etc.) or auditing an existing one.

---

## Prompt Template

```text
Integrate payment gateway: {gateway_name}

Required components:

1. Gateway adapter (apps/payments/gateways/{gateway_name}.py)
   - create_intent(amount, currency, reference, return_url, webhook_url) -> IntentResponse
   - verify_signature(payload: bytes, signature: str) -> None  (raises on mismatch)
   - parse(payload: bytes) -> GatewayEvent
   - fetch_status(intent_id: str) -> GatewayStatus  (for reconciliation)
   - refund(payment, amount) -> RefundResponse

2. Configuration
   - Secret keys in env vars (NEVER in code):
     * {GW}_PUBLIC_KEY
     * {GW}_SECRET_KEY
     * {GW}_WEBHOOK_SECRET
   - Gateway base URL configurable (sandbox vs prod)
   - Timeouts: connect 5s, read 10s

3. Webhook endpoint
   - URL: /payments/webhook/{gateway_name}/
   - CSRF-exempt, POST-only
   - Verify signature BEFORE any processing
   - Idempotent via PaymentEvent.gateway_event_id unique constraint
   - Returns 200 on success, 401 on bad signature, 400 on parse failure
   - Logs raw payload to PaymentEvent.raw_payload (audit trail)

4. Service layer (apps/payments/services.py)
   - create_payment_intent(order) — server-authoritative amount
   - handle_webhook(gateway, payload, signature) — verify + dedupe + transition
   - Side effects (email, invoice, stock) via Celery, not inline

5. Order linkage
   - Payment.order ForeignKey
   - On payment.succeeded webhook: append OrderEvent(PAID), decrement stock
   - On payment.failed webhook: append OrderEvent(PAYMENT_FAILED), release reservation

6. Reconciliation
   - Hourly Celery beat task: query gateway for any Payment stuck INITIATED > 1h
   - Synthesize a webhook-equivalent event and process through the same handler

7. Refunds
   - Staff-only endpoint
   - Creates a negative-amount Payment row linked to original
   - Submits to gateway, awaits webhook confirmation
   - Appends OrderEvent(REFUNDED) on success

8. Tests
   - Unit: signature verification (valid, invalid, expired)
   - Unit: idempotency (same event_id processed twice = one state change)
   - Integration: full flow with gateway sandbox
   - Integration: webhook arrives before return URL (race condition)
   - Integration: webhook never arrives → reconciliation picks it up

Security:
- Never log full payment payloads in INFO/DEBUG (PII, possible PAN)
- Whitelist gateway IPs at nginx where the gateway publishes them
- HMAC verification uses constant-time comparison (hmac.compare_digest)
- Webhook secret rotated on staff turnover or suspected leak

Forbidden:
- ❌ Marking order paid in the return URL view
- ❌ Skipping signature verification for "testing"
- ❌ Storing PAN, CVV, full card numbers
- ❌ Synchronous email/PDF generation inside webhook handler
- ❌ Calling gateway from frontend with secret key
```

---

## Pakistan-Specific Gateways (Context)

- **JazzCash**, **EasyPaisa** — mobile wallet, dominant locally; webhook conventions differ from international gateways
- **HBL**, **MeezanPay**, **Faysal DigiBank** — bank-issued gateways for card payments
- **Bank transfer / Pay on delivery** — common for B2B agro buyers; treat as a "manual" gateway with admin-confirmed status transition

## Checklist

- [ ] Adapter implements all required methods
- [ ] Webhook endpoint live and signature-verified
- [ ] Reconciliation job scheduled in Celery beat
- [ ] Refund flow tested in sandbox
- [ ] PaymentEvent table populated with raw payloads
- [ ] Sentry alerts on webhook signature failures (possible attack)
- [ ] Sandbox + prod credentials documented in ops runbook
