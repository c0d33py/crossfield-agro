from __future__ import annotations

from django.core.cache import cache
from django.db.models import QuerySet

from apps.seo.models import PageMetadata, Redirect, RobotsRule

# Cache layer for hot-path lookups (fire on every request via middleware/context
# processor). Per .claude/rules/performance.md: low-level caching for selector
# results, invalidated on post_save signals.
PAGE_META_TTL = 5 * 60  # 5 minutes
REDIRECT_TTL = 5 * 60

# Sentinel so we can cache "no row exists" misses too
_MISS = object()


def _meta_key(path: str) -> str:
    return f"seo:meta:{path}"


def _redirect_key(path: str) -> str:
    return f"seo:redirect:{path}"


def get_metadata_for_path(path: str) -> PageMetadata | None:
    key = _meta_key(path)
    cached = cache.get(key, _MISS)
    if cached is not _MISS:
        return cached
    row = PageMetadata.objects.filter(path=path).first()
    cache.set(key, row, PAGE_META_TTL)
    return row


def get_active_redirect(source_path: str) -> Redirect | None:
    key = _redirect_key(source_path)
    cached = cache.get(key, _MISS)
    if cached is not _MISS:
        return cached
    row = Redirect.objects.filter(source_path=source_path, is_active=True).first()
    cache.set(key, row, REDIRECT_TTL)
    return row


def get_active_robots_rules() -> QuerySet[RobotsRule]:
    # Robots rules query is small + low-traffic; not worth caching the queryset.
    return RobotsRule.objects.filter(is_active=True).order_by("position", "id")


def invalidate_metadata(path: str) -> None:
    cache.delete(_meta_key(path))


def invalidate_redirect(source_path: str) -> None:
    cache.delete(_redirect_key(source_path))
