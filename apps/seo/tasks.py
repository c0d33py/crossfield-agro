from __future__ import annotations

from django.db.models import F

from celery import shared_task


@shared_task(name="seo.increment_redirect_hits")
def increment_redirect_hits(redirect_id: int) -> None:
    from apps.seo.models import Redirect

    Redirect.objects.filter(pk=redirect_id).update(hits=F("hits") + 1)
