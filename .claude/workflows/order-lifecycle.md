# Order Lifecycle

## States

```text
PENDING → CONFIRMED → PAID → PROCESSING → SHIPPED → DELIVERED → COMPLETED
                                  ↓
                              CANCELLED  (terminal, from any pre-SHIPPED state)
                                  ↓
                              REFUNDED   (terminal, from PAID/COMPLETED)
```

## State Definitions

| State        | Meaning                                                  | Next state(s)              |
|--------------|----------------------------------------------------------|----------------------------|
| `PENDING`    | Order created, payment not yet attempted/confirmed       | CONFIRMED, CANCELLED       |
| `CONFIRMED`  | Inventory reserved; awaiting payment webhook             | PAID, CANCELLED            |
| `PAID`       | Payment webhook verified; stock decremented              | PROCESSING, REFUNDED       |
| `PROCESSING` | Warehouse picking/packing                                | SHIPPED, CANCELLED         |
| `SHIPPED`    | Dispatched with tracking number                          | DELIVERED                  |
| `DELIVERED`  | Carrier confirmed delivery                               | COMPLETED, REFUNDED        |
| `COMPLETED`  | Delivered + grace period passed; no disputes             | REFUNDED                   |
| `CANCELLED`  | Terminal — order voided pre-shipment                     | —                          |
| `REFUNDED`   | Terminal — funds returned (partial or full)              | —                          |

## Implementation

**Status is computed**, not stored on `Order`. Source of truth is `OrderEvent`:

```python
class OrderEvent(models.Model):
    order = models.ForeignKey("Order", related_name="events", on_delete=models.PROTECT)
    event_type = models.CharField(max_length=32, choices=OrderEventType.choices)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["order", "-created_at"])]


class Order(models.Model):
    # ... fields ...

    @property
    def current_status(self) -> OrderEventType:
        latest = self.events.order_by("-created_at").first()
        return latest.event_type if latest else OrderEventType.PENDING
```

## State Transitions

All transitions go through `orders.services.transition_order(order, to_state, actor=None, metadata=None)`:

```python
ALLOWED_TRANSITIONS = {
    OrderEventType.PENDING:    {OrderEventType.CONFIRMED, OrderEventType.CANCELLED},
    OrderEventType.CONFIRMED:  {OrderEventType.PAID, OrderEventType.CANCELLED},
    OrderEventType.PAID:       {OrderEventType.PROCESSING, OrderEventType.REFUNDED},
    OrderEventType.PROCESSING: {OrderEventType.SHIPPED, OrderEventType.CANCELLED},
    OrderEventType.SHIPPED:    {OrderEventType.DELIVERED},
    OrderEventType.DELIVERED:  {OrderEventType.COMPLETED, OrderEventType.REFUNDED},
    OrderEventType.COMPLETED:  {OrderEventType.REFUNDED},
}


def transition_order(*, order: Order, to_state, actor=None, metadata=None) -> OrderEvent:
    current = order.current_status
    if to_state not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidOrderTransition(f"{current} → {to_state} not allowed")
    with transaction.atomic():
        return OrderEvent.objects.create(
            order=order, event_type=to_state, actor=actor, metadata=metadata or {}
        )
```

## Side Effects per Transition

| Transition              | Side Effects                                                  |
|-------------------------|---------------------------------------------------------------|
| `* → CONFIRMED`         | Reserve stock (15-min hold)                                   |
| `* → PAID`              | Decrement stock; send confirmation email; generate invoice    |
| `* → PROCESSING`        | Notify warehouse system                                       |
| `* → SHIPPED`           | Send shipped email with tracking; update carrier API         |
| `* → DELIVERED`         | Send delivery email; start review-request grace timer         |
| `* → COMPLETED`         | Final receipt email; release any held escrow                  |
| `* → CANCELLED`         | Release reservation; restock; send cancellation email         |
| `* → REFUNDED`          | Trigger refund via gateway; send refund email                 |

All side effects dispatched as **Celery tasks** from the transition service, not inline.

## Auto-Transitions (Celery Beat)

- `CONFIRMED` orders with no payment after 30 min → `CANCELLED`
- `DELIVERED` orders untouched for 14 days → `COMPLETED`
- Stuck `PROCESSING` (> 5 days) → alert ops, no auto-transition

## Querying State Efficiently

For list views with many orders, computing `current_status` per-order is N+1.
Use a denormalized read column **populated by signal on `OrderEvent.save`**:

```python
# Order.cached_status — for list views and filters
# Order.events     — for audit trail and re-derivation
```

The cached column is a read optimization, NOT the source of truth. Always
re-derive from events when auditing or migrating.

## Cancellation Semantics

- Customer-initiated cancellation: allowed in `PENDING`, `CONFIRMED`
- Admin-initiated cancellation: allowed in `PENDING`, `CONFIRMED`, `PROCESSING`
- After `SHIPPED`: no cancellation — only `REFUNDED` after return

## Refund Semantics

- Allowed in: `PAID`, `DELIVERED`, `COMPLETED`
- Partial refunds tracked via `metadata.refund_amount` on the `REFUNDED` event
- Multiple partial refunds: multiple `REFUNDED` events with cumulative tracking
