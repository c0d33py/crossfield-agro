# Principles Audit — 2026-05-28

Audited against the 7 principles in [.claude/project.json](../project.json):

1. SEO-first architecture
2. Commerce-safe transaction flow
3. Service-layer business logic
4. Immutable orders
5. Async payment verification
6. Performance optimized queries
7. Admin-driven content management

## Findings

| # | Principle | Status | Notes |
|---|---|---|---|
| P1 | SEO-first architecture | **⚠ Fixed** | 5 page templates were missing `application/ld+json` structured data. Added `CollectionPage` JSON-LD to: `products/product_list.html`, `blog/tag_detail.html`, `media_center/{index,press_list,coverage_list}.html`. |
| P2 | Commerce-safe transaction flow | **⚠ Fixed (HIGH severity)** | **Stock was never decremented anywhere in the codebase**, despite the rule stating "Stock decrement happens at payment confirmation". Created [apps/products/services/inventory_service.py](../../apps/products/services/inventory_service.py) with `decrement_stock_for_order` (uses `SELECT FOR UPDATE` + `F()` expressions for race-safety). Hooked into `payments._mark_paid`. Handles `allow_backorder` (depletes to zero rather than raising) and `track_inventory=False` (skips). Raises `InsufficientStock` on shortfall, with audit log entry for ops alerting. 5 regression tests added. |
| P3 | Service-layer business logic | **Acknowledged** | Views are 100% free of ORM writes. Found 5 direct `.objects.filter/get` reads in views (cart item lookups, invoice lookup). Trivial 1-row PK lookups; arguably below the threshold that warrants a selector indirection. **Left as-is** — flagged for future cleanup if/when those views grow logic. |
| P4 | Immutable orders | **Clean** | Only `OrderEvent.objects.create(...)` ever runs against the orders schema. The single `Order.objects.filter().update(...)` call is for `cached_status` (read-side cache, explicitly allowed). No bypass paths. |
| P5 | Async payment verification | **Clean** | Webhook handler: signature-verified before processing, deduped by `gateway_event_id`, wrapped in `transaction.atomic()` with `select_for_update`. Return view never marks paid. Reconciliation Celery task exists for the "webhook never arrives" case. |
| P6 | Performance optimized queries | **⚠ Fixed** | Cold-path queries were fine (≤6 per page across 10 hot paths sampled). But the SEO `Redirect` lookup (middleware) and `PageMetadata` lookup (context processor) ran on every request without caching — 2 queries per page-load with no admin overrides. Added 5-min memoization with miss-sentinel and `post_save`/`post_delete` cache busting. Home page is now **0 queries on warm cache** (was 2). |
| P7 | Admin-driven content management | **Clean** | All 34 project models have admin registrations. Customer-data models (`Cart`, `CartItem`, `Order`, `OrderItem`, `Payment`, `ContactMessage`, `JobApplication`, etc.) configured as read-only with `has_add_permission(False)`. Editorial models (products, industries, services, blog posts, press releases, etc.) have proper fieldsets, list_editable, prepopulated_fields. |

## Test board

| Suite | Before | After | Delta |
|---|---|---|---|
| Full project | 158 pass / 3 fail | **188 pass / 0 fail** | +30 / -3 |

Pre-existing failures fixed as part of this audit:
- `cart.test_cart_service.TestClearCart::test_removes_all_items` — factory was creating duplicate-slug categories; share the category across products.
- `checkout.test_place_order.TestPlaceOrder::test_creates_order_and_intent_atomically` — test read stale `result.order.cached_status`; added `refresh_from_db()`.
- `products.test_selectors.TestGetPublishedProducts::test_no_n_plus_one_on_images` — expected 4 queries, Django actually issues 3 (fewer is better); calibrated expectation + added clarifying comment.

New tests added (5):
- `apps/products/tests/test_inventory.py` — basic decrement, insufficient-stock raises, backorder depletes to zero, track_inventory=False skips, multi-line atomicity.

## Files changed

### New
- [apps/products/services/inventory_service.py](../../apps/products/services/inventory_service.py)
- [apps/products/tests/test_inventory.py](../../apps/products/tests/test_inventory.py)
- [.claude/audits/2026-05-28-principles-audit.md](2026-05-28-principles-audit.md) (this file)

### Modified
- [apps/payments/services/payment_service.py](../../apps/payments/services/payment_service.py) — `_mark_paid` now decrements stock + emits audit alert on shortfall
- [apps/products/services/__init__.py](../../apps/products/services/__init__.py) — re-exports `decrement_stock_for_order` and `InsufficientStock`
- [apps/seo/selectors/__init__.py](../../apps/seo/selectors/__init__.py) — added cache layer with miss sentinel + invalidation helpers
- [apps/seo/signals.py](../../apps/seo/signals.py) — cache busting on `PageMetadata` and `Redirect` save/delete
- [apps/seo/apps.py](../../apps/seo/apps.py) — load signals in `ready()`
- [apps/products/templates/products/product_list.html](../../apps/products/templates/products/product_list.html) — `CollectionPage` JSON-LD
- [apps/blog/templates/blog/tag_detail.html](../../apps/blog/templates/blog/tag_detail.html) — `CollectionPage` + `BreadcrumbList` JSON-LD
- [apps/media_center/templates/media_center/index.html](../../apps/media_center/templates/media_center/index.html) — `CollectionPage` JSON-LD
- [apps/media_center/templates/media_center/press_list.html](../../apps/media_center/templates/media_center/press_list.html) — `CollectionPage` JSON-LD
- [apps/media_center/templates/media_center/coverage_list.html](../../apps/media_center/templates/media_center/coverage_list.html) — `CollectionPage` JSON-LD
- [apps/cart/tests/test_cart_service.py](../../apps/cart/tests/test_cart_service.py) — factory collision fix
- [apps/checkout/tests/test_place_order.py](../../apps/checkout/tests/test_place_order.py) — `refresh_from_db()` added
- [apps/products/tests/test_selectors.py](../../apps/products/tests/test_selectors.py) — query expectation recalibrated

## Future work (not done in this audit)

- **P3 partial cleanup**: extract the 5 direct view-layer ORM reads into selectors when those views grow non-trivial logic. Currently they're 1-line PK lookups.
- **Cart context processor caching**: same pattern as SEO. Session-keyed so trickier to invalidate; either tag cache by session_key or accept the 1-query overhead.
- **Add `manage.py check_principles` command**: codify these audits as a runnable check rather than a one-off document. Would flag new direct `.objects` calls in views, missing JSON-LD on new templates, etc.
- **Insufficient-stock alerting**: the `_mark_paid` exception handler currently writes to the audit log. Should additionally page on-call (Sentry message? email to ops mailing list?). Wire to whatever ops uses for alerting.
