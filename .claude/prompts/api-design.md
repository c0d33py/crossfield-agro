# Prompt: API Design

Use this when designing or extending a REST API endpoint (DRF or vanilla Django views).

---

## Prompt Template

```text
Design API endpoint(s) for: {feature}

For each endpoint, define:
- HTTP method + URL (kebab-case, slug-based, versioned under /api/v1/)
- Auth requirement (anonymous / authenticated / staff)
- Request shape (serializer / form schema)
- Response shape (serializer schema, status codes)
- Idempotency (GET/PUT/DELETE idempotent; POST with Idempotency-Key header where needed)
- Rate limit (per-IP and/or per-user)
- Errors (status codes + error code + human message)

Implementation must follow:
- Views are thin — parse request, call service, serialize response
- Business logic in services/, queries in selectors/
- Validation via DRF serializer OR validators.py — never inline in view
- Permission classes at view level; deeper authz inside services
- All writes inside transaction.atomic()
- Side effects dispatched as Celery tasks

Response conventions:
- 200: success with body
- 201: created (POST) with resource body and Location header
- 204: success with no body (DELETE)
- 400: validation error — {"errors": {field: [messages]}, "code": "validation_error"}
- 401: missing/invalid auth
- 403: authenticated but not authorized
- 404: resource not found
- 409: conflict (e.g., out of stock at checkout)
- 422: business rule violation — {"code": "domain_error_code", "message": "..."}
- 429: rate limited
- 500: server error (Sentry-captured)

Pagination:
- Cursor-based for high-cardinality lists (products, orders)
- Page-number for admin/staff lists
- Default page size 20, max 100

Filtering / sorting:
- Whitelist allowed fields explicitly
- No arbitrary __in lookups from query params

Versioning:
- /api/v1/ prefix
- Breaking changes → /api/v2/
- Deprecation header for sunset endpoints

Documentation:
- Generate OpenAPI schema via drf-spectacular
- Every endpoint must have description, request/response examples
```

---

## Commerce-Specific Endpoints

| Endpoint                              | Notes                                              |
|---------------------------------------|----------------------------------------------------|
| `POST /api/v1/cart/items/`            | Idempotency-Key recommended; rate-limited          |
| `GET /api/v1/cart/`                   | Recomputes totals server-side                      |
| `POST /api/v1/checkout/`              | Re-validates stock + recomputes totals             |
| `POST /api/v1/orders/`                | Creates immutable order; returns payment intent    |
| `GET /api/v1/orders/{id}/status/`     | Polled by frontend during payment                  |
| `POST /api/v1/payments/webhook/{gw}/` | CSRF-exempt; signature-verified; idempotent        |

## Forbidden

- ❌ Accepting `price`, `total`, or `currency` in request body for order/checkout
- ❌ Returning internal IDs that leak business intel (use UUIDs or slugs)
- ❌ Exposing stack traces in 500 responses
- ❌ Unbounded list endpoints (no pagination)
