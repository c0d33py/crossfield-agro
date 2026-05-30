# Feature Development Workflow

## 1. Define

- Write a one-paragraph spec: what user need, what success looks like
- Identify the app(s) the feature touches
- Identify whether commerce flow is affected → if yes, apply `commerce-rules.md`
- Identify SEO impact → new indexable URLs need `seo` app integration

## 2. Design

- Sketch the data model — new tables, new fields, migrations
- Sketch the service-layer interface (function signatures)
- Identify Celery tasks needed (emails, webhooks, generation)
- Identify cache keys to invalidate
- Identify admin / staff workflows

## 3. Build (in this order)

1. **Models + migrations** — create, review SQL, apply
2. **Services** — write business logic with `transaction.atomic()`
3. **Selectors** — read queries optimized with `select_related`/`prefetch_related`
4. **Validators** — input shape + business rule checks
5. **Views** — thin controllers calling services
6. **URLs** — kebab-case, slug-based
7. **Templates** — server-rendered, SEO-tagged
8. **Admin** — list_display, search_fields, list_filter, raw_id_fields for FKs
9. **Tasks** — Celery offload for side effects
10. **Tests** — unit (services), integration (views), e2e (commerce flows)

## 4. SEO Integration

- Register URL in sitemap
- Add metadata (title, description, og, canonical) via `seo` app
- Add JSON-LD structured data appropriate to page type
- Verify mobile rendering + Core Web Vitals

## 5. Performance Check

- Run `django-debug-toolbar` on the page — zero N+1
- Add caching for read-heavy paths
- Verify all FK reads use `select_related`

## 6. Security Review

- CSRF on all POST endpoints
- Rate limiting on sensitive endpoints
- Permission checks at view AND service layer
- No raw SQL; no `|safe` on user content

## 7. Test

- Unit tests for every service function (happy + error paths)
- Integration tests for view → service → DB
- Commerce flows: full e2e (cart → checkout → order → webhook → confirmation)
- Run `pytest` + coverage; target ≥ 80% for services

## 8. Document

- Update relevant `.claude/` rules if a new pattern emerged
- Add admin help_text on new model fields
- Note any operational requirements (env vars, Celery queues) in deploy docs

## 9. Ship

- Follow `deployment-checklist.md`
