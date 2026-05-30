from __future__ import annotations

from django.utils import timezone

from celery import shared_task


@shared_task(name="cart.purge_inactive_carts")
def purge_inactive_carts(inactivity_days: int = 14) -> int:
    """Daily Celery Beat: delete carts untouched beyond the inactivity window."""
    from apps.cart.models import Cart

    cutoff = timezone.now() - timezone.timedelta(days=inactivity_days)
    deleted, _ = Cart.objects.filter(updated_at__lt=cutoff).delete()
    return deleted
