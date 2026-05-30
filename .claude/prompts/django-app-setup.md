# Prompt: Django App Setup

Use this prompt to scaffold a new Django app inside `apps/`.

---

## Prompt Template

```text
Create a new Django app: {app_name}

Location: apps/{app_name}/
Registered in: config/settings/base.py under INSTALLED_APPS as "apps.{app_name}"

Required structure:
- apps.py (with proper AppConfig: name="apps.{app_name}", verbose_name)
- models.py
- admin.py
- urls.py (app_name = "{app_name}")
- views.py
- forms.py
- validators.py
- services/__init__.py
- selectors/__init__.py
- tasks.py (Celery)
- signals.py (only if cross-app events needed)
- migrations/__init__.py
- templates/{app_name}/
- tests/__init__.py, test_services.py, test_views.py

Architecture compliance:
- Views are thin — call into services/selectors only
- All writes wrapped in transaction.atomic() inside services/
- All reads use select_related/prefetch_related inside selectors/
- Side effects (email, webhooks, PDFs) dispatched as Celery tasks

Admin:
- Register each model with sensible list_display, search_fields, list_filter
- Use raw_id_fields for ForeignKeys to high-cardinality models
- Add readonly_fields for snapshot/audit data

SEO (if app exposes public URLs):
- Register URLs with the seo app for metadata
- Add to sitemap via django.contrib.sitemaps
- Render JSON-LD appropriate to page type

Tests:
- Unit tests for every public service function (happy + error)
- Integration test for the primary view
- No mocking of the database — use real DB transactions
```

---

## Checklist after scaffolding

- [ ] App added to `INSTALLED_APPS`
- [ ] URLs included in `config/urls.py`
- [ ] Initial migration created and applied
- [ ] Admin pages render without error
- [ ] At least one passing test
- [ ] Black + isort + flake8 clean
