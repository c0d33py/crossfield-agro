from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.products.models import Category, Product, ProductImage, ProductVariant
from apps.products.tasks import (
    generate_image_thumbnails,
    invalidate_catalog_cache,
    regenerate_product_sitemap,
)


@receiver(post_save, sender=Product)
def _on_product_saved(sender, instance: Product, created: bool, **kwargs) -> None:
    invalidate_catalog_cache.delay(product_id=instance.pk)
    regenerate_product_sitemap.delay()


@receiver(post_delete, sender=Product)
def _on_product_deleted(sender, instance: Product, **kwargs) -> None:
    invalidate_catalog_cache.delay(product_id=instance.pk)
    regenerate_product_sitemap.delay()


@receiver(post_save, sender=Category)
def _on_category_saved(sender, instance: Category, **kwargs) -> None:
    invalidate_catalog_cache.delay()


@receiver(post_save, sender=ProductImage)
def _on_image_saved(sender, instance: ProductImage, created: bool, **kwargs) -> None:
    if created:
        generate_image_thumbnails.delay(instance.pk)
    invalidate_catalog_cache.delay(product_id=instance.product_id)


@receiver(post_save, sender=ProductVariant)
def _on_variant_saved(sender, instance: ProductVariant, **kwargs) -> None:
    invalidate_catalog_cache.delay(product_id=instance.product_id)
