# Performance Rules

## Caching (Redis)

- Per-view cache for anonymous, GET-only pages (home, product list, blog index)
- Template fragment caching for expensive partials (header nav, footer, product grid)
- Low-level caching for selector results (key: model + version)
- Cache invalidation on model `post_save` / `post_delete` via signals → Celery task
- TTLs: pages 5min, fragments 15min, selectors 1hr (override per case)

## Query Optimization

- `select_related()` for ForeignKey / OneToOne reads
- `prefetch_related()` for reverse FK / M2M reads
- Use `.only()` / `.defer()` when fetching wide rows for narrow uses
- Index every field used in `filter()`, `order_by()`, or `JOIN`
- Use `django-debug-toolbar` in dev — N+1 queries are bugs, not optimizations
- Aggregate with `annotate()` / `Sum()` server-side — never count in Python

## Async via Celery

Offload to Celery:
- Order confirmation emails
- Invoice PDF generation
- Sitemap regeneration
- Image processing / thumbnail generation
- Payment webhook follow-up actions
- Analytics event ingestion

Never block a request on:
- Outbound HTTP (except payment intent creation, with timeout)
- PDF generation
- Image resizing
- Email sending

## Static & Media Assets

- CDN for `/static/` and `/media/` in production
- WhiteNoise or nginx for static serving (never Django in prod)
- Images: WebP/AVIF, responsive `<picture>` with `srcset`
- Lazy load below-fold images (`loading="lazy"`)
- Bundle + minify CSS/JS via Django Compressor or build pipeline
- Long cache headers on hashed asset filenames

## Database

- Connection pooling via `CONN_MAX_AGE = 60` minimum, pgbouncer in prod
- Read replicas for reporting / analytics queries (when scale demands)
- Long-running queries → Celery + materialized views, not request-time

## Frontend

- Defer non-critical JS
- Preconnect to CDN / gateway origins
- Inline critical CSS for above-fold
- Avoid layout shift (reserve image dimensions, font-display: swap)

## Measurement

- Sentry performance monitoring on production
- Track p50, p95, p99 response times per endpoint
- Alert on p95 > 1s for catalog pages, > 2s for checkout
