"""Inject per-URL metadata override into template context as `seo_meta`."""

from __future__ import annotations

from apps.seo.selectors import get_metadata_for_path


def seo_metadata(request) -> dict:
    try:
        meta = get_metadata_for_path(request.path)
        return {"seo_meta": meta}
    except Exception:
        return {"seo_meta": None}
