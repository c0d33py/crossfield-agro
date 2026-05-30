# Prompt: eCommerce Module Generator

Use this when generating a new commerce-domain Django app (`cart`, `checkout`,
`orders`, `payments`, `shipping`, `invoices`).

---

## Prompt Template

```text
Generate Django app: {module}

Required components:
- models       (commerce-safe design — see constraints below)
- services/    (business logic, transactional writes)
- selectors/   (optimized reads)
- validators   (input + business rule checks)
- admin        (sensible list_display, search, filters, raw_id_fields)
- urls + views (thin controllers)
- webhook handler (if payments — with signature verification + idempotency)
- tasks        (Celery offloads for emails, PDFs, side effects)
- tests        (unit for services, integration for views, e2e for commerce flow)

Commerce-safety constraints:
1. Orders are immutable — state lives in OrderEvent rows, not on Order.status
2. All totals recomputed server-side; never trust posted prices
3. Cart stores product_id + quantity only — no price snapshots
4. OrderItem snapshots: product_name, unit_price, sku at creation time
5. Payment webhook is the source of truth — redirect view does NOT mark paid
6. Webhook handler MUST verify signature AND be idempotent (dedup by event_id)
7. Stock decrement happens on PAID transition (webhook), not order creation
8. All cross-model writes inside transaction.atomic()
9. Side effects (email, invoice, decrement) dispatched as Celery tasks

SEO-ready endpoints (for catalog-adjacent apps):
- Slug-based URLs (kebab-case)
- Canonical URL set
- JSON-LD structured data appropriate to page type
- Registered in sitemap

Security:
- CSRF on all POST
- Rate limit on add-to-cart, checkout-submit, webhook
- Permission checks at view AND service layer
- Never log payment payloads with PAN/CVV

Performance:
- select_related / prefetch_related on all multi-row reads
- No N+1 — verify with django-debug-toolbar
- Cache product reads; invalidate on save via signal
```

---

## Per-Module Specifics

### `cart`
- Cart belongs to session OR user (merge on login)
- 14-day inactivity TTL via Celery beat cleanup
- `add_item`, `update_quantity`, `remove_item`, `clear` services
- Totals recomputed on every read — never cached on the row

### `checkout`
- Validates cart contents (re-check stock + active)
- Collects addresses + shipping method + payment method
- Hands off to `orders.services.create_order` then `payments.services.create_payment_intent`

### `orders`
- `Order` (immutable header) + `OrderItem` (snapshots) + `OrderEvent` (state log)
- `current_status` is computed from latest event
- All transitions through `transition_order` service with allowed-transition table

### `payments`
- `Payment` row per intent; `PaymentEvent` log of webhook events
- `create_payment_intent`, `handle_webhook`, `reconcile_pending_payments`
- Gateway abstraction: support pluggable gateways (Stripe-like, JazzCash, EasyPaisa, etc.)

### `shipping`
- Rate table; method per order
- Tracking number stored on `OrderEvent(SHIPPED).metadata`
- Carrier API integration via Celery

### `invoices`
- Sequential, immutable invoice numbers per fiscal year
- PDF generated on PAID event via Celery
- Signed-URL download
