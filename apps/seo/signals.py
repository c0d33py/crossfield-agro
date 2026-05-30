"""
Invalidate SEO selector caches on model save / delete so admin edits take
effect immediately rather than waiting for TTL expiry.
"""

from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.seo.models import PageMetadata, Redirect
from apps.seo.selectors import invalidate_metadata, invalidate_redirect


@receiver(post_save, sender=PageMetadata)
@receiver(post_delete, sender=PageMetadata)
def _bust_meta_cache(sender, instance: PageMetadata, **kwargs) -> None:
    invalidate_metadata(instance.path)


@receiver(post_save, sender=Redirect)
@receiver(post_delete, sender=Redirect)
def _bust_redirect_cache(sender, instance: Redirect, **kwargs) -> None:
    invalidate_redirect(instance.source_path)
