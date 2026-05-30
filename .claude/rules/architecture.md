# Architecture Rules

## System Flow

```text
Request → Middleware → View → Service Layer → Selector → ORM → DB
                                  ↓
                              Celery Task (async side effects)
                                  ↓
                              Webhook / Email / Audit Log
```

## Commerce Flow

```text
Cart → Checkout → Order → Payment Intent → Gateway → Webhook → Order Confirmed
```

## Core Principles

- **No direct DB calls in views** — go through services or selectors
- **All commerce logic in services** — pricing, totals, state transitions
- **Orders are append-only** — never UPDATE order rows; insert state-change records
- **Payments are event-driven** — webhook is the source of truth, not the redirect

## Modular Monolith

- One Django project, many apps under `apps/`
- Apps communicate via service-layer imports, NOT direct model imports across boundaries
- Cross-app side effects use Celery tasks or signals (sparingly)
- Each app owns its models; other apps consume them via that app's selectors

## Service Layer Contract

A service function:
- Accepts plain Python primitives or domain objects (not request objects)
- Returns a domain object or raises a domain exception
- Wraps its writes in `transaction.atomic()`
- Emits side effects (emails, webhooks) via Celery, not inline

```python
# Good
def create_order(*, user: User, cart: Cart, shipping_address: Address) -> Order:
    with transaction.atomic():
        order = Order.objects.create(...)
        for item in cart.items.all():
            OrderItem.objects.create(order=order, **item.snapshot())
        send_order_confirmation.delay(order.id)
    return order

# Bad
def create_order_view(request):
    Order.objects.create(...)  # business logic in view
```

## Selector Layer Contract

- Pure read functions
- Optimized with `select_related` / `prefetch_related`
- Return querysets or domain objects, never HTTP responses
- No writes, no side effects

## Forbidden Patterns

- ❌ Fat models with business logic methods that mutate other models
- ❌ Signals doing complex cross-app work (use Celery tasks instead)
- ❌ Circular imports between apps (extract to a shared `core` app)
- ❌ Storing computed totals on `Cart` — always recompute on read
