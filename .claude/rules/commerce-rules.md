# Commerce Rules (CRITICAL)

These rules are non-negotiable. Violations cause data loss, financial loss, or fraud.

## Cart Rules

- Cart belongs to **a session OR a user** — never both ambiguously
- Session carts merge into user cart on login (additive, dedup by product)
- Cart expires after inactivity window (default: 14 days)
- Cart `items` store `product_id` and `quantity` only — never price (price is computed live)
- Cart totals are **always recomputed on read** — never stored on the cart row
- Adding to cart validates: product exists, is active, quantity > 0, stock available
- Cart is NOT an order — losing it is acceptable; losing an order is not

## Order Rules

- Orders are **immutable** after creation
- Order state transitions are append-only — insert into `OrderEvent`, never UPDATE `Order.status`
- Order items **snapshot** product data at creation time:
  - `product_id` (reference)
  - `product_name` (snapshot — survives renames)
  - `unit_price` (snapshot — survives price changes)
  - `quantity`
  - `sku` (snapshot)
- Once paid, an order can ONLY transition forward (paid → processing → shipped → delivered)
- Cancellation is a new event (`CANCELLED`), not a deletion
- Refunds are tracked separately and link back to the original order

## Payment Rules

- Payments are **async confirmed** via gateway webhook
- The redirect-back URL is for UX only — **never** marks an order as paid
- Webhook handler MUST:
  - Verify signature/HMAC before processing
  - Be idempotent (same `event_id` processed twice = one state change)
  - Log every received event to `PaymentEvent` table (raw payload included)
  - Update order state inside `transaction.atomic()`
- Payment intent created server-side; client receives only the token/redirect URL
- Never store: PAN, CVV, full card number, CVC

## Pricing Rules

- Pricing is **server-authoritative** — frontend may DISPLAY price but never SUBMIT it
- On checkout, server recomputes:
  - Line totals (qty × current unit price)
  - Discounts (re-evaluated from current coupon state)
  - Shipping (re-evaluated from current rate table + address)
  - Taxes (re-evaluated from current jurisdiction rules)
  - Grand total
- If client-displayed total differs from server-computed total beyond rounding,
  show user a "price changed" notice and require re-confirmation

## Inventory Rules (when enabled)

- Stock decrement happens at **payment confirmation**, not at cart-add or order-create
- Reserved/pending stock concept for in-flight checkouts (15-min hold)
- Negative stock is impossible — use DB-level constraint
- Overselling: explicit business decision per product (allow vs. reject)

## Coupons / Discounts

- Coupons validated server-side at checkout AND at payment-confirmation
- One-time coupons marked used inside the payment transaction
- Stacking rules explicit and tested

## Invoice Rules

- Invoice generated on payment confirmation (Celery task)
- Invoice number is sequential and immutable per fiscal year
- Invoice PDF stored; URL signed for customer download

## Forbidden

- ❌ `Order.objects.update(status='paid')` — must go through service + event log
- ❌ Trusting `request.POST['total']`
- ❌ Marking paid in the redirect-back view
- ❌ Deleting orders to "cancel" them
- ❌ Reusing invoice numbers
- ❌ Editing cart items after checkout has been submitted
