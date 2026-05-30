"""Local development settings."""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, INSTALLED_APPS, MIDDLEWARE, env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Dev runs over plain HTTP on localhost — payment intent return/webhook URLs
# must match the scheme the browser actually uses, or the redirect after
# /checkout/payment/ lands on https://localhost which the dev server can't serve.
SITE_DOMAIN = env("SITE_DOMAIN", default="127.0.0.1:8000")
SITE_SCHEME = env("SITE_SCHEME", default="http")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-do-not-use-in-prod")

# SQLite for local dev — no postgres required.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Dummy cache so dev works without Redis.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Debug toolbar
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]
INTERNAL_IPS = ["127.0.0.1"]

# Emails go to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Celery: run tasks eagerly unless explicitly told otherwise
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
CELERY_TASK_EAGER_PROPAGATES = True
# No result backend in dev — eager tasks don't need one.
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True

# Dev: plain static files storage (no manifest hashing).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
