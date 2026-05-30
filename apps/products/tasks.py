from __future__ import annotations

import logging

from django.core.cache import cache

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="products.invalidate_catalog_cache")
def invalidate_catalog_cache(product_id: int | None = None) -> None:
    """
    Bumps catalog cache version keys. Cheap; called from signals on product/category save.
    Read-side selectors include the version in their cache key.
    """
    cache.delete_many(
        [
            "products:list:v",
            "products:category-tree:v",
        ]
    )
    if product_id is not None:
        cache.delete(f"products:detail:{product_id}")


@shared_task(name="products.regenerate_product_sitemap")
def regenerate_product_sitemap() -> None:
    """
    Triggered on product publish/archive. The actual sitemap is built by
    django.contrib.sitemaps and cached; this task only invalidates the cache.
    """
    cache.delete("sitemap:products")
    logger.info("Product sitemap cache invalidated")


@shared_task(name="products.generate_image_thumbnails")
def generate_image_thumbnails(product_image_id: int) -> None:
    """
    Generate resized variants (WebP/AVIF) for a newly uploaded ProductImage.
    Placeholder — wire to PIL/Pillow + storage when image pipeline is finalized.
    """
    from apps.products.models import ProductImage

    try:
        image = ProductImage.objects.get(pk=product_image_id)
    except ProductImage.DoesNotExist:
        logger.warning("ProductImage %s missing — skipping thumbnail generation", product_image_id)
        return
    logger.info("TODO: generate thumbnails for ProductImage %s (%s)", image.pk, image.image.name)
