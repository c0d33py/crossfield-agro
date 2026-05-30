from __future__ import annotations

from celery import shared_task


@shared_task(name="payments.reconcile_pending")
def reconcile_pending() -> int:
    from apps.payments.services import reconcile_pending_payments

    return reconcile_pending_payments()
