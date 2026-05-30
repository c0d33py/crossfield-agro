# Deployment Checklist

## Pre-Deploy

### Code

- [ ] All tests pass on CI (unit, integration, ecommerce)
- [ ] No `print()`, no `console.log()`, no commented-out blocks
- [ ] No `DEBUG=True`, no hardcoded credentials
- [ ] Black + isort + flake8 clean
- [ ] Coverage ≥ 80% on changed files

### Migrations

- [ ] Migrations reviewed for backwards compatibility
- [ ] No destructive schema changes without a multi-step plan
- [ ] Run `manage.py makemigrations --check --dry-run` — no missing migrations
- [ ] Long-running migrations split (add column → backfill → enforce NOT NULL)

### Config

- [ ] Env vars added to production secret store (`.env.production`)
- [ ] New Celery queues registered in supervisor / systemd
- [ ] New scheduled tasks added to Celery Beat
- [ ] Logging configured for new modules

### Static / Media

- [ ] `collectstatic` succeeds
- [ ] CDN purge planned if asset URLs changed
- [ ] New image variants generated (Celery task triggered)

### SEO

- [ ] Sitemap regenerated for new URLs
- [ ] Canonical URLs verified
- [ ] No accidental `noindex` on new pages
- [ ] Google Search Console submission queued

### Performance

- [ ] New endpoints profiled — p95 < target
- [ ] Cache keys / TTLs reviewed
- [ ] No new N+1 queries (django-debug-toolbar verified)

### Security

- [ ] CSRF on all new POST endpoints
- [ ] Rate limits on new sensitive endpoints
- [ ] Permission checks at view + service layer
- [ ] Secret keys rotated if leaked or suspected

## Deploy

1. Tag release (`vYYYY.MM.DD-N`)
2. Put site in maintenance mode if migrations require it
3. Pull code on web + worker nodes
4. Install requirements (`pip install -r requirements.txt`)
5. Run migrations (`manage.py migrate`)
6. `collectstatic --noinput`
7. Restart gunicorn (graceful)
8. Restart Celery workers + beat
9. Lift maintenance mode
10. Smoke test: homepage, product page, add-to-cart, checkout stub, admin login

## Post-Deploy

- [ ] Monitor Sentry for 30 min — no new error classes
- [ ] Check p95 latency dashboards — within baseline
- [ ] Check Celery queue depth — draining normally
- [ ] Spot-check 5 product pages for SEO regressions (view-source)
- [ ] Verify a real test transaction end-to-end (cart → checkout → webhook → order)

## Rollback Trigger

Rollback immediately if:
- Error rate > 2× baseline for > 5 min
- Payment webhook failure rate > 1%
- p95 latency > 3× baseline
- Any data corruption observed

## Rollback Steps

1. Re-deploy previous tag
2. If migrations were applied, roll forward with a fix-migration (don't downgrade schema in prod)
3. Postmortem within 24h
