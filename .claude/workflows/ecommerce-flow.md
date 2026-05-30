# eCommerce Flow

## High-Level Pipeline

```text
Product → Add to Cart → Cart Review → Checkout → Order Creation
       → Payment Intent → Gateway → Webhook → Confirmation → Shipping → Delivered
```

## Step-by-Step

### 1. Product Discovery

- User lands on product page (`/products/<slug>/`)
- Selector fetches product + variants + images + related (single optimized query)
- SEO: `Product` + `Offer` JSON-LD rendered server-side
- "Add to Cart" CTA shows current stock state

### 2. Add to Cart

- POST `/cart/add/` with `product_id`, `quantity`, optional `variant_id`
- `cart.services.add_item(cart, product_id, quantity)`:
  - Validate product active + stock available
  - Dedup: if product already in cart, increment qty
  - Persist `CartItem` (product_id + quantity only — no price)
- Response: updated cart summary (item count, recomputed subtotal)

### 3. Cart Review

- GET `/cart/`
- Selector loads cart items + product snapshots
- **Totals recomputed server-side on every load** (never stored)
- User can update quantities / remove items
- "Proceed to Checkout" CTA — disabled if any item went out of stock

### 4. Checkout

- GET `/checkout/`
- Requires auth OR guest checkout with email
- Collects: shipping address, billing address, shipping method, payment method
- Server recomputes: line totals, discounts, shipping, taxes, grand total
- Displays final total; user confirms

### 5. Order Creation

- POST `/checkout/place-order/`
- `orders.services.create_order(user, cart, addresses, shipping_method)`:
  - `transaction.atomic()`
  - Re-validate all items (active, in stock)
  - Re-compute all totals from current data
  - Create `Order` (status: PENDING)
  - Create `OrderItem` rows with product snapshots
  - Create `OrderEvent` (event: CREATED)
  - Reserve stock (15-min hold)
  - Empty the cart
- Returns order ID + redirect to payment

### 6. Payment Intent

- `payments.services.create_payment_intent(order)`:
  - Server-side call to gateway with amount + order reference
  - Persist `Payment` row (status: INITIATED)
  - Return gateway redirect URL / client token
- User redirected to gateway-hosted page (or in-page widget)

### 7. Gateway Interaction

- User completes payment on gateway
- Gateway processes; user redirected back to `/checkout/return/`
- **Return view does NOT mark paid** — it only shows "Processing your payment…"

### 8. Webhook (source of truth)

- Gateway POSTs to `/payments/webhook/<gateway>/`
- `payments.services.handle_webhook(payload, signature)`:
  - Verify HMAC/signature
  - Lookup `event_id` — if already processed, return 200 (idempotent)
  - Persist raw event to `PaymentEvent`
  - `transaction.atomic()`:
    - Update `Payment.status` to SUCCEEDED / FAILED
    - If SUCCEEDED: append `OrderEvent(PAID)`, decrement stock, release reservation
    - If FAILED: append `OrderEvent(PAYMENT_FAILED)`, release reservation
  - Trigger Celery: `send_order_confirmation`, `generate_invoice`
- Return 200 to gateway

### 9. Confirmation

- User polls `/checkout/return/` (or websocket) for order status
- Once `PAID`, redirect to `/orders/<id>/confirmation/`
- Confirmation email already sent via Celery
- Invoice PDF available for download

### 10. Fulfillment

- Staff sees PAID order in admin
- Triggers `OrderEvent(PROCESSING)` → picking, packing
- On dispatch: `OrderEvent(SHIPPED)` with tracking number
- On delivery confirmation: `OrderEvent(DELIVERED)`
- Final state: `OrderEvent(COMPLETED)` (auto after grace period)

## Failure Paths

| Failure                          | Handling                                                  |
|----------------------------------|-----------------------------------------------------------|
| Stock gone between cart & order  | Reject order creation; show user; cart preserved          |
| Payment timeout                  | Order stays PENDING; reservation expires; user retries    |
| Webhook delayed                  | Order shows "Processing"; polling; eventual consistency   |
| Webhook never arrives            | Cron reconciliation job queries gateway after 1hr         |
| Duplicate webhook                | Idempotency via `event_id` — no double-state-change       |
| Gateway returns FAILED           | Order → PAYMENT_FAILED; user offered retry with new intent|
