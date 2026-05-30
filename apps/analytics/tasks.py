from __future__ import annotations

import logging
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="analytics.rollup_daily")
def rollup_daily(target_date_iso: str | None = None) -> int:
    """
    Aggregate PageView + Event for a given date (defaults to yesterday) into
    DailyRollup. Idempotent — re-running for the same date upserts.
    Returns the number of paths rolled up.
    """
    from apps.analytics.models import DailyRollup, Event, PageView

    if target_date_iso:
        target = date.fromisoformat(target_date_iso)
    else:
        target = date.today() - timedelta(days=1)

    views_by_path = (
        PageView.objects.filter(created_at__date=target)
        .values("path")
        .annotate(views=Count("id"), unique_sessions=Count("session_key", distinct=True))
    )
    events_by_path = (
        Event.objects.filter(created_at__date=target).values("path").annotate(events=Count("id"))
    )
    event_count_by_path = {row["path"]: row["events"] for row in events_by_path}

    count = 0
    with transaction.atomic():
        for row in views_by_path:
            DailyRollup.objects.update_or_create(
                path=row["path"],
                date=target,
                defaults={
                    "views": row["views"],
                    "unique_sessions": row["unique_sessions"],
                    "events": event_count_by_path.pop(row["path"], 0),
                },
            )
            count += 1
        # Paths that only had events but no pageviews
        for path, events in event_count_by_path.items():
            DailyRollup.objects.update_or_create(
                path=path,
                date=target,
                defaults={"views": 0, "unique_sessions": 0, "events": events},
            )
            count += 1

    logger.info("analytics.rollup_daily: %s paths rolled up for %s", count, target)
    return count
