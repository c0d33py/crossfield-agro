# Crosfield Agro Pakistan

A corporate + eCommerce hybrid platform for an agro-industrial supplier:
corporate site (home, about, industries, services, blog, careers, media) plus a
B2B-oriented product catalog with cart → checkout → orders → payments → shipping
→ invoices.

## Stack

| Layer    | Tech                              |
|----------|-----------------------------------|
| Backend  | Django 5 (modular monolith)       |
| Database | PostgreSQL (SQLite in dev)        |
| Cache    | Redis                             |
| Async    | Celery + Celery Beat              |
| Serving  | gunicorn + nginx + WhiteNoise     |

## Architecture

```text
Request → View (thin) → Service (logic) → Selector (reads) → ORM → DB
                              ↓
                         Celery (async side effects)
```

Apps live under `apps/`; settings under `config/settings/` (`base`,
`development`, `production`). See [CLAUDE.md](CLAUDE.md) and [.claude/](.claude/)
for the full architecture brief and non-negotiable rules.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in real values; never commit .env
python manage.py migrate
python manage.py runserver
```

Dev settings use SQLite, an in-memory cache, and eager Celery — no Postgres or
Redis required to run or test locally.

## Tests & quality

```bash
pytest                # full suite
black --check .       # formatting
isort --check-only .  # import order
flake8 .              # lint
```

CI runs all of the above on every push and pull request to `main`
(see [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Deployment

Production settings live in `config/settings/production.py` and read secrets
from environment variables only. The CI workflow currently runs lint + tests; it
does **not** deploy. Wire up a deploy job (VPS over SSH, a PaaS, or a container
registry) once target infrastructure and credentials exist.
