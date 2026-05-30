# Crosfield Agro Pakistan — Project Structure

```bash
crosfield_agro/
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── production.py
│   │   └── development.py
│   ├── urls.py
│   ├── celery.py
│   ├── logging.py
│   └── wsgi.py
│
├── apps/
│
│   # CORE
│   ├── core/
│   ├── accounts/
│
│   # CATALOG
│   ├── products/
│   ├── industries/
│   ├── services/
│
│   # COMMERCE
│   ├── cart/
│   ├── checkout/
│   ├── orders/
│   ├── payments/
│   ├── shipping/
│   ├── invoices/
│
│   # ENGAGEMENT
│   ├── blog/
│   ├── contact/
│   ├── careers/
│   ├── media_center/
│
│   # SYSTEM
│   ├── seo/
│   ├── analytics/
│   ├── audit/
│
├── templates/
├── static/
├── media/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── ecommerce/
│
├── deploy/
│   ├── nginx/
│   ├── gunicorn/
│   ├── scripts/
│
├── requirements.txt
└── manage.py
```

## Per-App Standard Layout

Every Django app under `apps/` follows this layout:

```bash
apps/<app_name>/
├── __init__.py
├── apps.py
├── models.py
├── admin.py
├── urls.py
├── views.py
├── forms.py
├── validators.py
├── services/           # business logic (write operations)
│   └── __init__.py
├── selectors/          # query logic (read operations)
│   └── __init__.py
├── api/                # DRF serializers + viewsets (optional)
│   ├── serializers.py
│   └── views.py
├── tasks.py            # Celery tasks
├── signals.py
├── migrations/
├── templates/<app_name>/
└── tests/
```

## Layer Responsibilities

| Layer       | Purpose                                                  |
|-------------|----------------------------------------------------------|
| `views`     | Thin controllers — parse request, call service, respond  |
| `services`  | Business logic, transactions, side effects               |
| `selectors` | Read queries with prefetch/select_related                |
| `validators`| Input validation, business rule checks                   |
| `tasks`     | Async work via Celery (emails, webhooks, reports)        |
| `signals`   | Cross-app event handling — use sparingly                 |
