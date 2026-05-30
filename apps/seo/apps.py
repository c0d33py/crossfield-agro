from django.apps import AppConfig


class SeoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.seo"
    label = "seo"
    verbose_name = "Central SEO metadata, redirects, structured data helpers"

    def ready(self) -> None:
        from . import signals  # noqa: F401
