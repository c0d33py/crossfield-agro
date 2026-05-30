from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.products"
    label = "products"
    verbose_name = "Products"

    def ready(self) -> None:
        from . import signals  # noqa: F401
