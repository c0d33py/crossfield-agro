# CLAUDE.md — Crosfield Agro Pakistan

This file is loaded into every Claude Code session. It is the **canonical project
brief**. Detailed rules live under [.claude/](.claude/) — this file is the index
and the non-negotiables.

---

## Project

**Crosfield Agro Pakistan** — a corporate + eCommerce hybrid platform:
- Corporate site (home, about, industries, services, blog, careers, media)
- Product catalog with B2B-oriented commerce (cart → checkout → orders → payments → shipping → invoices)
- SEO-first; agro-industrial buyers discover suppliers through search

## Stack

| Layer    | Tech                                  |
|----------|---------------------------------------|
| Backend  | Django (modular monolith)             |
| Database | PostgreSQL                            |
| Cache    | Redis                                 |
| Async    | Celery + Celery Beat                  |
| Hosting  | VPS / Cloud + nginx + gunicorn        |

## Architecture (modular monolith)

```text
Request → View (thin) → Service (logic) → Selector (reads) → ORM → DB
                              ↓
                         Celery (async side effects)
```

Per-app standard layout: `models`, `admin`, `urls`, `views`, `forms`,
`validators`, `services/`, `selectors/`, `tasks`, `signals`, `tests/`.
Full layout in [.claude/structure.md](.claude/structure.md).

### Modules

- **core**: home, about, pages
- **catalog**: products, industries, services
- **commerce**: cart, checkout, orders, payments, shipping, invoices
- **engagement**: blog, contact, careers, media_center
- **system**: accounts, seo, analytics, audit

---

## Non-negotiables (read before writing code)

### Layering

- Views are thin controllers. **No ORM calls, no business logic, no pricing in views.**
- All writes go through `services/` inside `transaction.atomic()`.
- All reads go through `selectors/` with `select_related` / `prefetch_related`.
- Side effects (email, PDF, webhooks, decrements) dispatched as **Celery tasks**, never inline.

### Commerce (CRITICAL — see [.claude/rules/commerce-rules.md](.claude/rules/commerce-rules.md))

- **Orders are immutable.** State lives in `OrderEvent` rows (event-sourced);
  `Order.current_status` is derived. Never `Order.objects.update(status=...)`.
- **Cart stores `product_id` + `quantity` only** — no price. Totals always recomputed on read.
- **Pricing is server-authoritative.** Never trust posted `price`/`total`. Recompute at checkout AND at payment confirmation.
- **OrderItem snapshots** product data (`product_name`, `unit_price`, `sku`) at creation — survives renames and price changes.
- **The payment webhook is the source of truth.** The redirect-back view never marks an order paid.
- **Webhook handlers must verify signature AND be idempotent** (dedup by `gateway_event_id`).
- **Stock decrements on PAID transition** (from webhook), not on cart-add or order-create.

### Security (see [.claude/rules/security.md](.claude/rules/security.md))

- CSRF on all state-changing endpoints. ORM-only DB access (no raw SQL).
- Rate-limit login, contact, checkout, cart-add, webhook (per-IP).
- Secrets in env vars only — never committed.
- Never log payment payloads with PAN/CVV. Never store PAN, CVV, full card numbers.
- HMAC verification uses `hmac.compare_digest` (constant-time).

### SEO (see [.claude/rules/seo.md](.claude/rules/seo.md))

- The `seo` app owns all metadata centrally.
- Every public URL: unique `<title>` (50–60), `<meta description>` (140–160), canonical, OG tags, Twitter card.
- JSON-LD structured data per page type (`Product`+`Offer`, `Article`, `Organization`, etc.) — server-rendered.
- Slug-based kebab-case URLs. Auto-generated XML sitemap (per model type).
- Core Web Vitals targets: LCP < 2.5s, INP < 200ms, CLS < 0.1.

### Performance (see [.claude/rules/performance.md](.claude/rules/performance.md))

- Redis caching for read-heavy paths; invalidate on `post_save` via signal → Celery.
- N+1 queries are bugs. Verify with `django-debug-toolbar` before merging.
- CDN for `/static/` and `/media/` in production.

---

## How to work in this codebase

### Before writing code

1. Read the relevant rule files under [.claude/rules/](.claude/rules/).
2. If the change touches commerce, re-read [commerce-rules.md](.claude/rules/commerce-rules.md) — it is the file most likely to be violated.
3. If adding a new app or feature, follow [.claude/workflows/feature-development.md](.claude/workflows/feature-development.md).

### When writing code

- Put logic in `services/` (writes) and `selectors/` (reads), not views.
- Wrap writes in `transaction.atomic()`.
- Dispatch side effects via Celery.
- For commerce changes: walk through [.claude/workflows/ecommerce-flow.md](.claude/workflows/ecommerce-flow.md) mentally — does your change preserve every invariant?
- Add regression tests in `tests/unit/`, `tests/integration/`, or `tests/ecommerce/`.

### Before merging

- Black + isort + flake8 clean.
- No N+1 (verified with debug-toolbar).
- Tests cover happy path + at least one error path.
- For commerce: the 4 validations in [.claude/workflows/bug-resolution.md](.claude/workflows/bug-resolution.md) §6.
- Follow [.claude/workflows/deployment-checklist.md](.claude/workflows/deployment-checklist.md) for releases.

---

## Pointers

| Topic                 | File                                                                     |
|-----------------------|--------------------------------------------------------------------------|
| Directory layout      | [.claude/structure.md](.claude/structure.md)                             |
| Code style            | [.claude/rules/code-style.md](.claude/rules/code-style.md)               |
| Architecture          | [.claude/rules/architecture.md](.claude/rules/architecture.md)           |
| Commerce invariants   | [.claude/rules/commerce-rules.md](.claude/rules/commerce-rules.md)       |
| Security              | [.claude/rules/security.md](.claude/rules/security.md)                   |
| SEO                   | [.claude/rules/seo.md](.claude/rules/seo.md)                             |
| Performance           | [.claude/rules/performance.md](.claude/rules/performance.md)             |
| UI / UX               | [.claude/rules/ui-ux.md](.claude/rules/ui-ux.md)                         |
| Bug fixing            | [.claude/rules/bug-fixing.md](.claude/rules/bug-fixing.md)               |
| Feature workflow      | [.claude/workflows/feature-development.md](.claude/workflows/feature-development.md) |
| Bug workflow          | [.claude/workflows/bug-resolution.md](.claude/workflows/bug-resolution.md)           |
| Deploy checklist      | [.claude/workflows/deployment-checklist.md](.claude/workflows/deployment-checklist.md) |
| eCommerce flow        | [.claude/workflows/ecommerce-flow.md](.claude/workflows/ecommerce-flow.md)           |
| Order lifecycle       | [.claude/workflows/order-lifecycle.md](.claude/workflows/order-lifecycle.md)         |
| Payment handling      | [.claude/workflows/payment-handling.md](.claude/workflows/payment-handling.md)       |
| New Django app        | [.claude/prompts/django-app-setup.md](.claude/prompts/django-app-setup.md)           |
| New commerce module   | [.claude/prompts/ecommerce-module-generator.md](.claude/prompts/ecommerce-module-generator.md) |
| API design            | [.claude/prompts/api-design.md](.claude/prompts/api-design.md)                       |
| SEO optimization      | [.claude/prompts/seo-optimization.md](.claude/prompts/seo-optimization.md)           |
| Payment integration   | [.claude/prompts/payment-integration.md](.claude/prompts/payment-integration.md)     |

---

## State of the project

The Django project itself (`crosfield_agro/`, `apps/`, `config/`) **does not exist yet**.
This repository currently contains only the `.claude/` guardrails and this `CLAUDE.md`.
When ready to scaffold, use [.claude/prompts/django-app-setup.md](.claude/prompts/django-app-setup.md)
as the per-app generator, starting with `config/` (settings, celery, urls) then `core`, `accounts`,
catalog modules, and finally commerce modules.
